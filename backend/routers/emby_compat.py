"""Emby 兼容 API 最小子集（Infuse / VidHub / SenPlayer 直连）。

实现依据：Jellyfin OpenAPI（https://api.jellyfin.org）与客户端抓包；
不参考任何 GPL 实现。原则：
- 未实现端点返回 200 + 空集合（empty_result），绝不 404 —— 兼容层稳定性关键。
- /Videos/{id}/stream 是唯一视频出口：经 StorageResolver 实时换链后 302，
  直链永不缓存/落库（即 CMS 302 服务的替代品）。
- 进度与 Web 端共表（playback_progress, source='library'），互通续播。

路由同时挂根路径与 /emby 前缀（main.py 注册两次）。
反代注意：Nginx 需把 /emby、/Users、/System、/Videos、/Items、/Sessions、/Shows
转发到后端（见 docs/library-player.md）。
"""
from __future__ import annotations

import asyncio
import logging
import secrets
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from config import config
from database import (
    get_library_files_by_content_id,
    get_progress,
    list_continue_watching,
    list_matched_library_files,
    save_progress,
)
from services.emby_mapper import (
    SERVER_ID,
    empty_result,
    library_view_dto,
    media_source_dto,
    ticks_to_seconds,
    to_base_item_dto,
)
from services.storage_resolver import get_resolver

logger = logging.getLogger(__name__)

router = APIRouter(tags=["emby-compat"])

EMBY_USER_ID = "javhub-emby-user"
METADATA_CONCURRENCY = 8

# 内存 token 表：单用户场景足够；服务重启后客户端 401 → 自动重新登录
_active_tokens: set[str] = set()


# ── 鉴权 ─────────────────────────────────────────────────────────


def _ensure_enabled() -> None:
    if not config.emby_compat_enabled:
        raise HTTPException(status_code=403, detail="Emby compat API is disabled")


def _extract_token(request: Request) -> str:
    token = (
        request.headers.get("X-Emby-Token")
        or request.headers.get("X-MediaBrowser-Token")
        or request.query_params.get("api_key")
        or ""
    )
    if not token:
        # Authorization: MediaBrowser ..., Token="xxx"
        auth = request.headers.get("Authorization") or request.headers.get("X-Emby-Authorization") or ""
        for part in auth.split(","):
            part = part.strip()
            if part.lower().startswith("token="):
                token = part.split("=", 1)[1].strip().strip('"')
                break
    return token


def _require_auth(request: Request) -> str:
    _ensure_enabled()
    token = _extract_token(request)
    if not token or token not in _active_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


def _user_dto() -> dict:
    return {
        "Id": EMBY_USER_ID,
        "ServerId": SERVER_ID,
        "Name": config.emby_compat_username,
        "HasPassword": True,
        "HasConfiguredPassword": True,
        "Policy": {"IsAdministrator": False, "EnableMediaPlayback": True},
        "Configuration": {"PlayDefaultAudioTrack": True, "SubtitleMode": "Default"},
    }


# ── 元数据辅助 ───────────────────────────────────────────────────


async def _metadata_for(codes: list[str]) -> dict[str, Optional[dict]]:
    from modules.info_client import get_info_client

    client = get_info_client()
    sem = asyncio.Semaphore(METADATA_CONCURRENCY)

    async def fetch(code: str):
        async with sem:
            try:
                return code, await client.get_video(code)
            except Exception:
                return code, None

    results = await asyncio.gather(*(fetch(code) for code in codes))
    return dict(results)


def _grouped_library() -> list[dict]:
    """matched 文件按番号归并，保持 first_seen_at desc 顺序。"""
    groups: dict[str, dict] = {}
    for row in list_matched_library_files():
        group = groups.setdefault(row["content_id"], {"content_id": row["content_id"], "files": []})
        group["files"].append(row)
    return list(groups.values())


# ── 认证与系统信息 ───────────────────────────────────────────────


@router.post("/Users/AuthenticateByName")
async def authenticate_by_name(request: Request):
    _ensure_enabled()
    try:
        body = await request.json()
    except Exception:
        body = {}
    username = str(body.get("Username") or body.get("username") or "")
    password = str(body.get("Pw") or body.get("pw") or body.get("Password") or "")
    if username != config.emby_compat_username or not config.emby_compat_password \
            or password != config.emby_compat_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_hex(20)
    _active_tokens.add(token)
    return {
        "User": _user_dto(),
        "SessionInfo": {"Id": uuid.uuid4().hex, "UserId": EMBY_USER_ID},
        "AccessToken": token,
        "ServerId": SERVER_ID,
    }


@router.get("/System/Info/Public")
async def system_info_public():
    _ensure_enabled()
    return {
        "ServerName": "JavHub",
        "Version": "4.8.8.0",
        "Id": SERVER_ID,
        "LocalAddress": "",
        "ProductName": "JavHub Emby Compat",
    }


@router.get("/System/Info")
async def system_info(request: Request):
    _require_auth(request)
    info = await system_info_public()
    info["OperatingSystem"] = "Linux"
    return info


@router.get("/Users/{user_id}")
async def get_user(user_id: str, request: Request):
    _require_auth(request)
    return _user_dto()


@router.get("/Users")
async def list_users(request: Request):
    _require_auth(request)
    return [_user_dto()]


# ── 媒体库浏览 ───────────────────────────────────────────────────


@router.get("/Users/{user_id}/Views")
async def user_views(user_id: str, request: Request):
    _require_auth(request)
    return {"Items": [library_view_dto()], "TotalRecordCount": 1, "StartIndex": 0}


@router.get("/UserViews")
async def user_views_alias(request: Request):
    return await user_views(EMBY_USER_ID, request)


@router.get("/Users/{user_id}/Items/Resume")
async def items_resume(user_id: str, request: Request, Limit: int = Query(12)):
    token = _require_auth(request)
    rows = [r for r in list_continue_watching(limit=Limit) if r.get("source") == "library"]
    codes = [r["content_id"] for r in rows]
    metadata = await _metadata_for(codes) if codes else {}
    items = []
    for row in rows:
        files = get_library_files_by_content_id(row["content_id"])
        if not files:
            continue
        items.append(to_base_item_dto(
            row["content_id"], metadata.get(row["content_id"]), files,
            progress=row, token=token,
        ))
    return {"Items": items, "TotalRecordCount": len(items), "StartIndex": 0}


@router.get("/Users/{user_id}/Items/Latest")
async def items_latest(user_id: str, request: Request, Limit: int = Query(16)):
    token = _require_auth(request)
    groups = _grouped_library()[:Limit]
    metadata = await _metadata_for([g["content_id"] for g in groups]) if groups else {}
    # Latest 返回裸数组（无 Items 包装）
    return [
        to_base_item_dto(g["content_id"], metadata.get(g["content_id"]), g["files"], token=token)
        for g in groups
    ]


@router.get("/Users/{user_id}/Items/{item_id}")
async def item_detail(user_id: str, item_id: str, request: Request):
    token = _require_auth(request)
    files = get_library_files_by_content_id(item_id)
    if not files:
        raise HTTPException(status_code=404, detail="Item not found")
    metadata = (await _metadata_for([item_id])).get(item_id)
    progress = get_progress(item_id, source="library")
    return to_base_item_dto(item_id, metadata, files, progress=progress, token=token, detailed=True)


@router.get("/Users/{user_id}/Items")
async def items_browse(
    user_id: str,
    request: Request,
    ParentId: Optional[str] = Query(None),
    StartIndex: int = Query(0, ge=0),
    Limit: int = Query(50, ge=1, le=200),
    SortBy: str = Query("DateCreated"),
    SortOrder: str = Query("Descending"),
    SearchTerm: Optional[str] = Query(None),
):
    token = _require_auth(request)
    groups = _grouped_library()

    if SearchTerm:
        needle = SearchTerm.strip().upper()
        groups = [
            g for g in groups
            if needle in g["content_id"].upper()
            or any(needle in str(f.get("name", "")).upper() for f in g["files"])
        ]

    primary_sort = SortBy.split(",")[0].strip()
    if primary_sort == "SortName":
        groups.sort(key=lambda g: g["content_id"])
        if SortOrder.startswith("Desc"):
            groups.reverse()
    elif SortOrder.startswith("Asc"):
        groups.reverse()  # 默认序是 first_seen desc

    total = len(groups)
    page = groups[StartIndex:StartIndex + Limit]
    metadata = await _metadata_for([g["content_id"] for g in page]) if page else {}
    items = [
        to_base_item_dto(g["content_id"], metadata.get(g["content_id"]), g["files"], token=token)
        for g in page
    ]
    return {"Items": items, "TotalRecordCount": total, "StartIndex": StartIndex}


@router.get("/Items/{item_id}/Images/Primary")
@router.get("/Items/{item_id}/Images/Primary/{index}")
async def item_primary_image(item_id: str, request: Request, index: int = 0):
    # 海报：302 到元数据封面（图片端点不少客户端不带 token，放宽鉴权只查 enabled）
    _ensure_enabled()
    metadata = (await _metadata_for([item_id])).get(item_id) or {}
    url = str(metadata.get("jacket_full_url") or metadata.get("jacket_thumb_url") or "")
    if not url:
        raise HTTPException(status_code=404, detail="No image")
    return RedirectResponse(url=url, status_code=302)


# ── 播放 ─────────────────────────────────────────────────────────


@router.get("/Items/{item_id}/PlaybackInfo")
@router.post("/Items/{item_id}/PlaybackInfo")
async def playback_info(item_id: str, request: Request):
    token = _require_auth(request)
    files = get_library_files_by_content_id(item_id)
    if not files:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "MediaSources": [media_source_dto(f, token=token) for f in files],
        "PlaySessionId": uuid.uuid4().hex,
    }


async def _resolve_stream(item_id: str, media_source_id: Optional[str]):
    files = get_library_files_by_content_id(item_id)
    if not files:
        raise HTTPException(status_code=404, detail="Item not found")
    chosen = files[0]
    if media_source_id and media_source_id.startswith("lib:"):
        try:
            file_id = int(media_source_id.split(":", 1)[1])
            chosen = next((f for f in files if f["id"] == file_id), chosen)
        except ValueError:
            pass
    try:
        resolver = get_resolver(chosen["backend"])
        return await resolver.resolve_play_url(chosen)
    except Exception as exc:
        logger.error("emby stream resolve failed for %s: %s", item_id, type(exc).__name__)
        raise HTTPException(status_code=502, detail="link resolve failed")


@router.get("/Videos/{item_id}/stream")
@router.get("/Videos/{item_id}/stream.{ext}")
async def video_stream(
    item_id: str,
    request: Request,
    ext: str = "",
    MediaSourceId: Optional[str] = Query(None),
):
    """核心视频出口：实时换链 → 302。Range 由 302 目标（115/Alist）原生处理。"""
    _require_auth(request)
    link = await _resolve_stream(item_id, MediaSourceId)
    if config.emby_compat_proxy_stream:
        # 兜底：客户端不跟随 302 时流式转发（默认关闭，吃服务器带宽）
        import httpx
        from fastapi.responses import StreamingResponse

        upstream_headers = dict(link.headers)
        if request.headers.get("range"):
            upstream_headers["Range"] = request.headers["range"]
        client = httpx.AsyncClient(timeout=None, follow_redirects=True)
        upstream = await client.send(
            client.build_request("GET", link.url, headers=upstream_headers), stream=True
        )

        async def body():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        passthrough = {
            k: v for k, v in upstream.headers.items()
            if k.lower() in ("content-type", "content-length", "content-range", "accept-ranges")
        }
        return StreamingResponse(body(), status_code=upstream.status_code, headers=passthrough)
    return RedirectResponse(url=link.url, status_code=302)


# ── 进度回写（与 Web 端共表）─────────────────────────────────────


async def _duration_seconds_for(item_id: str, body: dict) -> float:
    if body.get("RunTimeTicks"):
        return ticks_to_seconds(body["RunTimeTicks"])
    existing = get_progress(item_id, source="library")
    if existing and existing.get("duration_seconds"):
        return float(existing["duration_seconds"])
    metadata = (await _metadata_for([item_id])).get(item_id) or {}
    runtime_mins = metadata.get("runtime_mins") or 0
    return float(runtime_mins) * 60


async def _record_session_progress(request: Request) -> Response:
    _require_auth(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    item_id = str(body.get("ItemId") or "")
    if item_id:
        position = ticks_to_seconds(body.get("PositionTicks"))
        duration = await _duration_seconds_for(item_id, body)
        save_progress(item_id, "library", position, duration)
    return Response(status_code=204)


@router.post("/Sessions/Playing")
async def session_playing(request: Request):
    return await _record_session_progress(request)


@router.post("/Sessions/Playing/Progress")
async def session_progress(request: Request):
    return await _record_session_progress(request)


@router.post("/Sessions/Playing/Stopped")
async def session_stopped(request: Request):
    return await _record_session_progress(request)


@router.post("/Sessions/Capabilities/Full")
@router.post("/Sessions/Capabilities")
async def session_capabilities(request: Request):
    _require_auth(request)
    return Response(status_code=204)


# ── 未实现端点：200 + 空集合（绝不 404）──────────────────────────

EMPTY_COLLECTION_PATHS = (
    "/Shows/NextUp",
    "/Shows/Upcoming",
    "/Persons",
    "/Artists",
    "/Genres",
    "/Items/Filters",
    "/Items/Filters2",
    "/Users/{user_id}/Items/Suggestions",
    "/Movies/Recommendations",
)

for _path in EMPTY_COLLECTION_PATHS:
    async def _empty_endpoint(request: Request, user_id: str = "", **kwargs: Any):  # noqa: ANN401
        _require_auth(request)
        return empty_result()

    router.add_api_route(_path, _empty_endpoint, methods=["GET"], include_in_schema=False)


@router.get("/DisplayPreferences/{pref_id}")
async def display_preferences(pref_id: str, request: Request):
    _require_auth(request)
    return {"Id": pref_id, "SortBy": "SortName", "SortOrder": "Ascending", "CustomPrefs": {}}


@router.post("/DisplayPreferences/{pref_id}")
async def save_display_preferences(pref_id: str, request: Request):
    _require_auth(request)
    return Response(status_code=204)


@router.get("/Branding/Configuration")
async def branding(request: Request):
    _ensure_enabled()
    return {"LoginDisclaimer": "", "CustomCss": ""}
