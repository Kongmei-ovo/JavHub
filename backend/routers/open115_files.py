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
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from services.open115 import Open115AuthRequired, Open115Error, Open115File, open115_client
from services.playback_gateway import HLSPlaybackSessionStore

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
        "mtime": file.mtime,
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
    order: str | None = Query(None),
    asc: int | None = Query(None, ge=0, le=1),
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
        result = await open115_client.list_folder(cid, offset=offset, limit=limit, order=order, asc=asc)
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
async def stream_file(pick_code: str = Query(...), request: Request = None) -> RedirectResponse:
    """302 straight to the 115 direct link, signed for the calling client's UA.

    The browser <video> (or any client) follows the redirect with the same UA the
    link was issued for, so the bytes stream directly from 115's CDN and the
    backend never sits in the data path — the same direct-play trick the Emby
    compat layer uses for Infuse. Seeking (Range) goes straight to 115.
    """
    user_agent = (request.headers.get("user-agent") if request is not None else "") or open115_client.default_ua
    try:
        url = await open115_client.downurl(pick_code, user_agent)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    return RedirectResponse(url=url, status_code=302, headers={"Cache-Control": "no-store"})


# ── 115 转码 HLS 同源代理 ──────────────────────────────────────────
# mkv/avi 等容器浏览器原生放不了,但 115 能服务端转码成 H.264 HLS。该转码流没有 CORS 头,
# hls.js 不能跨域直拉 → 后端同源代理 + 递归改写分片地址(主清单→子清单→ts 都改成本端 token 地址)。
# 安全同 playback.py 的库资源 HLS:分片地址只来自 115 自家清单(token 映射),不暴露任意 URL,无 SSRF 面;
# session_id 与 per-target token 都是随机密钥。网盘文件无库资源 id,用常量 scope,安全由 token 承担。
_open115_hls_sessions = HLSPlaybackSessionStore()
_OPEN115_HLS_SCOPE = 0

_open115_hls_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
    trust_env=False,
)


def _open115_hls_path(session_id: str, target_token: str) -> str:
    return f"/api/v1/open115/files/hls/{session_id}/{target_token}"


def _rewrite_open115_hls(text: str, base_url: str, session) -> str:
    def register(raw_uri: str) -> str:
        target_url = urljoin(base_url, raw_uri)
        token = _open115_hls_sessions.register_target(session, target_url)
        return _open115_hls_path(session.session_id, token)

    def rewrite_uri_attr(match) -> str:
        return f'URI="{register(match.group(1))}"'

    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if 'URI="' in stripped:
            stripped = re.sub(r'URI="([^"]+)"', rewrite_uri_attr, stripped)
        if stripped and not stripped.startswith("#"):
            stripped = register(stripped)
        out.append(stripped)
    return "\n".join(out) + "\n"


async def _proxy_open115_hls(session, target_token: str, request: Request | None) -> Response:
    target_url = session.targets.get(target_token)
    if not target_url:
        raise HTTPException(status_code=410, detail="HLS 播放目标已过期")
    headers = {
        "User-Agent": session.user_agent,
        "Accept": request.headers.get("accept", "*/*") if request is not None else "*/*",
    }
    if request is not None and request.headers.get("range"):
        headers["Range"] = request.headers["range"]
    try:
        upstream = await _open115_hls_client.get(target_url, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="115 HLS 上游请求失败") from exc
    if upstream.status_code >= 400:
        raise HTTPException(status_code=502, detail="115 HLS 上游暂不可用")

    content_type = str(upstream.headers.get("content-type") or "application/octet-stream")
    content = upstream.content
    looks_like_manifest = (
        content.lstrip().startswith(b"#EXTM3U")
        or "mpegurl" in content_type.lower()
        or target_url.split("?", 1)[0].lower().endswith(".m3u8")
    )
    response_headers = {"Cache-Control": "no-store", "Access-Control-Allow-Origin": "*"}
    if looks_like_manifest:
        content = _rewrite_open115_hls(
            content.decode("utf-8", errors="replace"), target_url, session
        ).encode("utf-8")
        content_type = "application/vnd.apple.mpegurl"
    else:
        for header in ("content-range", "accept-ranges"):
            if upstream.headers.get(header):
                response_headers[header.title()] = upstream.headers[header]
    return Response(
        content=content,
        status_code=upstream.status_code,
        media_type=content_type,
        headers=response_headers,
    )


@router.get("/hls")
async def hls_master(pick_code: str = Query(...), request: Request = None) -> Response:
    """115 转码 HLS 主清单(同源代理)。浏览器把这个 URL 交给 hls.js 当源,即可在网页里
    播放 mkv/avi 等原生放不了的格式 —— 115 服务端转 H.264 HLS,数据面分片仍是 CDN→浏览器。"""
    user_agent = (request.headers.get("user-agent") if request is not None else "") or open115_client.default_ua
    try:
        urls = await open115_client.video_transcode_urls(pick_code)
    except Open115Error as exc:
        raise _http_error(exc) from exc
    if not urls:
        raise HTTPException(
            status_code=425,
            detail="115 转码尚未就绪，请稍后重试",
            headers={"Retry-After": "15"},
        )
    session_id = _open115_hls_sessions.create(
        resource_id=_OPEN115_HLS_SCOPE,
        root_url=urls[0].url,
        user_agent=user_agent,
    )
    session = _open115_hls_sessions.get(session_id, _OPEN115_HLS_SCOPE)
    return await _proxy_open115_hls(session, "root", request)


@router.get("/hls/{session_id}/{target_token}")
async def hls_target(session_id: str, target_token: str, request: Request = None) -> Response:
    session = _open115_hls_sessions.get(session_id, _OPEN115_HLS_SCOPE)
    if session is None:
        raise HTTPException(status_code=410, detail="HLS 播放会话已过期，请重新打开播放地址")
    return await _proxy_open115_hls(session, target_token, request)
