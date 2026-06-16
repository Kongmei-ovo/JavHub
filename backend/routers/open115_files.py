"""115 drive file browsing, preview and management.

Browse the whole 115 drive, preview video (transcode HLS) and images (UA proxy),
and manage files (folder/rename/move/copy/delete/search). Auth lives in
routers/open115.py; this router is file-focused.

Per Open115Client's contract, access tokens and signed download/transcode URLs
are request-scoped: they are returned to the caller for immediate use and never
logged, cached, or persisted.
"""
from __future__ import annotations

import mimetypes
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.open115 import Open115AuthRequired, Open115Error, Open115File, open115_client

router = APIRouter(prefix="/api/v1/open115/files", tags=["open115-files"])


def _http_error(exc: Open115Error) -> HTTPException:
    if isinstance(exc, Open115AuthRequired):
        return HTTPException(status_code=409, detail={"message": exc.api_message, "code": "open115_unbound"})
    return HTTPException(status_code=502, detail=exc.api_message)


def _file_dict(file: Open115File) -> dict[str, Any]:
    return {
        "file_id": file.file_id,
        "parent_id": file.parent_id,
        "name": file.name,
        "is_dir": file.is_dir,
        "size": file.size,
        "duration": file.duration,
        "extension": file.extension,
        "pick_code": file.pick_code,
    }


class FolderCreateRequest(BaseModel):
    pid: str = "0"
    name: str


class RenameRequest(BaseModel):
    file_id: str
    name: str


class MoveRequest(BaseModel):
    file_ids: list[str] = Field(default_factory=list)
    to_cid: str


class CopyRequest(BaseModel):
    file_ids: list[str] = Field(default_factory=list)
    to_cid: str


class DeleteRequest(BaseModel):
    file_ids: list[str] = Field(default_factory=list)
    parent_id: str | None = None


@router.get("")
async def list_files(
    cid: str = Query("0"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    keyword: str | None = Query(None),
) -> dict[str, Any]:
    keyword = (keyword or "").strip()
    try:
        if keyword:
            files = await open115_client.search_files(keyword, cid=cid, offset=offset, limit=limit)
            return {
                "files": [_file_dict(item) for item in files],
                "path": [],
                "count": len(files),
                "offset": offset,
                "limit": limit,
                "keyword": keyword,
            }
        result = await open115_client.list_folder(cid, offset=offset, limit=limit)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {
        "files": [_file_dict(item) for item in result["files"]],
        "path": result["path"],
        "count": result["count"],
        "offset": offset,
        "limit": limit,
    }


@router.post("/folder")
async def create_folder(req: FolderCreateRequest) -> dict[str, Any]:
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name 不能为空")
    try:
        file_id = await open115_client.mkdir(req.pid or "0", name)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"file_id": file_id}


@router.post("/rename")
async def rename(req: RenameRequest) -> dict[str, Any]:
    try:
        await open115_client.rename_file(req.file_id, req.name)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"ok": True}


@router.post("/move")
async def move(req: MoveRequest) -> dict[str, Any]:
    try:
        moved = await open115_client.move_files(req.file_ids, req.to_cid)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"ok": True, "moved": moved}


@router.post("/copy")
async def copy(req: CopyRequest) -> dict[str, Any]:
    try:
        copied = await open115_client.copy_files(req.file_ids, req.to_cid)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"ok": True, "copied": copied}


@router.post("/delete")
async def delete(req: DeleteRequest) -> dict[str, Any]:
    try:
        await open115_client.delete_files(req.file_ids, req.parent_id)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"ok": True}


@router.get("/video")
async def video_sources(pick_code: str = Query(...)) -> dict[str, Any]:
    try:
        urls = await open115_client.video_transcode_urls(pick_code)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"sources": [{"url": item.url, "definition": item.definition, "desc": item.desc} for item in urls]}


@router.get("/download")
async def download(pick_code: str = Query(...), request: Request = None) -> dict[str, Any]:
    user_agent = request.headers.get("user-agent", "") if request is not None else ""
    try:
        url = await open115_client.downurl(pick_code, user_agent)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return {"url": url}


@router.get("/image")
async def image_preview(
    pick_code: str = Query(...),
    ext: str = Query(""),
    request: Request = None,
) -> StreamingResponse:
    user_agent = (request.headers.get("user-agent") if request is not None else "") or open115_client.default_ua
    try:
        url = await open115_client.downurl(pick_code, user_agent)
    except Open115Error as exc:
        raise _http_error(exc) from exc

    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, trust_env=False)
    try:
        upstream = await client.send(
            client.build_request("GET", url, headers={"User-Agent": user_agent}),
            stream=True,
        )
        upstream.raise_for_status()
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail="无法获取图片") from exc

    # 115's CDN often serves images as octet-stream; coerce to a real image type
    # (from the file extension) so browsers render it inline.
    content_type = upstream.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        guessed = mimetypes.guess_type(f"x.{ext.lstrip('.')}")[0] if ext.strip() else None
        content_type = guessed or "image/jpeg"

    async def _body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(_body(), media_type=content_type)


@router.get("/stream")
async def stream_file(pick_code: str = Query(...), request: Request = None) -> StreamingResponse:
    """Range-aware proxy for direct playback/download of a 115 file.

    Used for videos 115 hasn't transcoded (no HLS). Forwards the client's Range
    header and passes upstream range/length/type back so the browser can seek.
    """
    user_agent = (request.headers.get("user-agent") if request is not None else "") or open115_client.default_ua
    try:
        url = await open115_client.downurl(pick_code, user_agent)
    except Open115Error as exc:
        raise _http_error(exc) from exc

    upstream_headers = {"User-Agent": user_agent}
    range_header = request.headers.get("range") if request is not None else None
    if range_header:
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=None, follow_redirects=True, trust_env=False)
    try:
        upstream = await client.send(
            client.build_request("GET", url, headers=upstream_headers),
            stream=True,
        )
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail="无法获取文件") from exc

    passthrough = {
        key: upstream.headers[key]
        for key in ("content-range", "content-length", "accept-ranges")
        if key in upstream.headers
    }
    content_type = upstream.headers.get("content-type") or "application/octet-stream"

    async def _body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        _body(),
        status_code=upstream.status_code,
        headers=passthrough,
        media_type=content_type,
    )
