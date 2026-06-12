"""播放链路端点：实时换链 + 播放进度 + 继续观看。

本路由响应一律不进响应缓存（直链有时效）。
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from database import (
    get_movie_resource,
    get_library_files_by_content_id,
    get_progress,
    list_continue_watching,
    save_progress,
)
from services.open115 import Open115Error, open115_client
from services.playback_gateway import PlaybackContext, hls_sessions
from services.storage_resolver import get_resolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/playback", tags=["playback"])

VALID_SOURCES = ("library", "online")

playback_hls_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
)


def _playback_resource(resource_id: int) -> dict:
    resource = get_movie_resource(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="播放资源不存在")
    if (
        resource.get("provider") != "open115"
        or resource.get("resource_type") != "video"
        or resource.get("status") != "ready"
        or not resource.get("pick_code")
    ):
        raise HTTPException(status_code=409, detail="资源当前不可播放")
    return resource


async def _create_hls_session(resource: dict, user_agent: str) -> str:
    try:
        urls = await open115_client.video_transcode_urls(str(resource["pick_code"]))
    except Open115Error as exc:
        raise HTTPException(
            status_code=425,
            detail="115 转码暂不可用，请稍后重试",
            headers={"Retry-After": "15"},
        ) from exc
    if not urls:
        raise HTTPException(
            status_code=425,
            detail="115 转码尚未就绪，请稍后重试",
            headers={"Retry-After": "15"},
        )
    return hls_sessions.create(
        resource_id=int(resource["id"]),
        root_url=urls[0].url,
        user_agent=user_agent,
    )


@router.get("/resources/{resource_id}/stream")
async def stream_movie_resource(
    resource_id: int,
    request: Request,
    mode: str = Query("auto"),
    caller: str = Query(""),
):
    resource = _playback_resource(resource_id)
    try:
        context = PlaybackContext.build(
            user_agent=request.headers.get("user-agent", ""),
            accept=request.headers.get("accept", ""),
            mode=mode,
            extension=str(resource.get("extension") or ""),
            caller_hint=caller,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if context.preferred_mode == "hls":
        session_id = await _create_hls_session(resource, context.user_agent)
        return RedirectResponse(
            url=f"/api/v1/playback/resources/{resource_id}/hls/{session_id}/master.m3u8",
            status_code=307,
            headers={"Cache-Control": "no-store"},
        )

    try:
        direct_url = await open115_client.downurl(
            str(resource["pick_code"]),
            context.user_agent,
        )
    except Open115Error as exc:
        if context.requested_mode != "auto" or not context.accepts_hls:
            raise HTTPException(status_code=502, detail="115 原画换链失败") from exc
        session_id = await _create_hls_session(resource, context.user_agent)
        return RedirectResponse(
            url=f"/api/v1/playback/resources/{resource_id}/hls/{session_id}/master.m3u8",
            status_code=307,
            headers={"Cache-Control": "no-store"},
        )
    return RedirectResponse(
        url=direct_url,
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )


def _session_or_gone(resource_id: int, session_id: str):
    session = hls_sessions.get(session_id, resource_id)
    if session is None:
        raise HTTPException(status_code=410, detail="HLS 播放会话已过期，请重新打开播放地址")
    return session


def _hls_proxy_path(resource_id: int, session_id: str, target_token: str) -> str:
    return f"/api/v1/playback/resources/{resource_id}/hls/{session_id}/{target_token}"


def _rewrite_hls_manifest(
    *,
    text: str,
    base_url: str,
    resource_id: int,
    session,
) -> str:
    def register(raw_uri: str) -> str:
        target_url = urljoin(base_url, raw_uri)
        target_token = hls_sessions.register_target(session, target_url)
        return _hls_proxy_path(resource_id, session.session_id, target_token)

    def rewrite_uri_attribute(match: re.Match[str]) -> str:
        return f'URI="{register(match.group(1))}"'

    rewritten = []
    for line in text.splitlines():
        stripped = line.strip()
        if 'URI="' in stripped:
            stripped = re.sub(r'URI="([^"]+)"', rewrite_uri_attribute, stripped)
        if stripped and not stripped.startswith("#"):
            stripped = register(stripped)
        rewritten.append(stripped)
    return "\n".join(rewritten) + "\n"


async def _proxy_hls_target(
    *,
    resource_id: int,
    session_id: str,
    target_token: str,
    request: Request,
):
    session = _session_or_gone(resource_id, session_id)
    target_url = session.targets.get(target_token)
    if not target_url:
        raise HTTPException(status_code=410, detail="HLS 播放目标已过期")
    headers = {
        "User-Agent": session.user_agent,
        "Accept": request.headers.get("accept", "*/*"),
    }
    if request.headers.get("range"):
        headers["Range"] = request.headers["range"]
    try:
        upstream = await playback_hls_client.get(target_url, headers=headers)
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
    response_headers = {"Cache-Control": "no-store"}
    if looks_like_manifest:
        content = _rewrite_hls_manifest(
            text=content.decode("utf-8", errors="replace"),
            base_url=target_url,
            resource_id=resource_id,
            session=session,
        ).encode("utf-8")
        content_type = "application/vnd.apple.mpegurl"
    else:
        for header in ("content-range", "accept-ranges"):
            if upstream.headers.get(header):
                response_headers[header.title()] = upstream.headers[header]
    return Response(content=content, media_type=content_type, headers=response_headers)


@router.get("/resources/{resource_id}/hls/{session_id}/master.m3u8")
async def proxy_open115_hls_master(resource_id: int, session_id: str, request: Request):
    return await _proxy_hls_target(
        resource_id=resource_id,
        session_id=session_id,
        target_token="root",
        request=request,
    )


@router.get("/resources/{resource_id}/hls/{session_id}/{target_token}")
async def proxy_open115_hls_target(
    resource_id: int,
    session_id: str,
    target_token: str,
    request: Request,
):
    return await _proxy_hls_target(
        resource_id=resource_id,
        session_id=session_id,
        target_token=target_token,
        request=request,
    )


def _public_file(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "path": row.get("path"),
        "size": row.get("size"),
        "backend": row.get("backend"),
        "modified_at": row.get("modified_at"),
    }


@router.get("/library/{content_id}")
async def library_play(content_id: str, file_id: Optional[int] = Query(None)) -> dict[str, Any]:
    """换链播放入口。直链实时获取，永不缓存/落库。"""
    files = get_library_files_by_content_id(content_id)
    if not files:
        raise HTTPException(status_code=404, detail={"message": "番号不在云盘库中"})
    chosen = files[0]
    if file_id is not None:
        chosen = next((f for f in files if f["id"] == file_id), None)
        if chosen is None:
            raise HTTPException(status_code=404, detail={"message": "指定文件不存在或已删除"})
    try:
        resolver = get_resolver(chosen["backend"])
        link = await resolver.resolve_play_url(chosen)
    except KeyError:
        raise HTTPException(status_code=500, detail={"message": f"不支持的存储后端: {chosen['backend']}"})
    except Exception as exc:
        logger.error("resolve play url failed for %s: %s", content_id, type(exc).__name__)
        raise HTTPException(status_code=502, detail={"message": "换链失败，请稍后重试"})

    progress = get_progress(content_id, source="library")
    return {
        "file": _public_file(chosen),
        "files": [_public_file(f) for f in files],
        "play": {"url": link.url, "kind": link.kind, "headers": link.headers},
        "progress": {
            "position_seconds": progress["position_seconds"] if progress else 0,
            "duration_seconds": progress["duration_seconds"] if progress else 0,
            "completed": bool(progress and progress.get("completed")),
        },
    }


class ProgressRequest(BaseModel):
    source: str = "library"
    position_seconds: float
    duration_seconds: float = 0


@router.put("/progress/{content_id}")
async def put_progress(content_id: str, req: ProgressRequest):
    if req.source not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail="source 必须是 library 或 online")
    return save_progress(content_id, req.source, req.position_seconds, req.duration_seconds)


@router.get("/progress/{content_id}")
async def read_progress(content_id: str, source: Optional[str] = Query(None)):
    progress = get_progress(content_id, source=source)
    if not progress:
        return {"content_id": content_id, "position_seconds": 0, "duration_seconds": 0, "completed": 0}
    return progress


@router.get("/continue")
async def continue_watching(limit: int = Query(12, ge=1, le=50)):
    """继续观看：进度行 + 元数据（标题/封面）懒加载合并。"""
    rows = list_continue_watching(limit)
    if not rows:
        return {"items": []}

    from modules.info_client import get_info_client

    client = get_info_client()

    async def enrich(row: dict) -> dict:
        item = {
            "content_id": row["content_id"],
            "source": row["source"],
            "position_seconds": row["position_seconds"],
            "duration_seconds": row["duration_seconds"],
            "updated_at": row.get("updated_at"),
            "video": None,
        }
        try:
            item["video"] = await client.get_video(row["content_id"])
        except Exception:
            pass  # 元数据缺失不阻断列表
        return item

    items = await asyncio.gather(*(enrich(r) for r in rows))
    return {"items": list(items)}
