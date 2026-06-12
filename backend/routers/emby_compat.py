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
import hashlib
import logging
import secrets
import uuid
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from config import config
from database import (
    get_movie_resource,
    get_progress,
    list_movie_resources,
    list_continue_watching,
    save_progress,
)
from services.emby_mapper import (
    SERVER_ID,
    empty_result,
    library_view_dto,
    media_source_dto,
    online_media_source_dto,
    ticks_to_seconds,
    to_base_item_dto,
)

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


async def _catalog_page(
    *,
    start_index: int,
    limit: int,
    search_term: Optional[str] = None,
    sort_by: str = "release_date:desc",
    random_seed: Optional[str] = None,
) -> dict:
    from modules.info_client import get_info_client

    client = get_info_client()
    page_size = min(limit, 100)
    page = (start_index // page_size) + 1
    offset = start_index % page_size
    items: list[dict] = []
    total_count = 0
    needed = offset + limit
    first_request = True
    while len(items) < needed:
        result = await client.list_catalog_videos(
            page=page,
            page_size=page_size,
            q=search_term,
            sort_by=sort_by,
            random_seed=random_seed,
            include_total=first_request,
        )
        if first_request:
            total_count = int(result.get("total_count") or 0)
            first_request = False
        batch = list(result.get("data") or [])
        items.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return {
        "data": items[offset:offset + limit],
        "total_count": total_count,
    }


EMBY_CATALOG_SORT_FIELDS = {
    "datecreated": "release_date",
    "premieredate": "release_date",
    "productionyear": "release_date",
    "sortname": "title",
    "name": "title",
    "communityrating": "score",
    "criticrating": "score",
    "runtime": "runtime_mins",
    "random": "random",
}


def _catalog_sort_spec(sort_by: str, sort_order: str) -> str:
    fields = [value.strip() for value in str(sort_by or "DateCreated").split(",") if value.strip()]
    directions = [
        value.strip().lower()
        for value in str(sort_order or "Descending").split(",")
        if value.strip()
    ]
    if not directions:
        directions = ["descending"]
    if len(directions) == 1:
        directions *= len(fields)
    elif len(directions) != len(fields):
        raise HTTPException(status_code=400, detail="SortOrder must match SortBy")

    result = []
    for field, direction in zip(fields, directions):
        catalog_field = EMBY_CATALOG_SORT_FIELDS.get(field.lower())
        if not catalog_field:
            raise HTTPException(status_code=400, detail=f"Unsupported SortBy field: {field}")
        if direction not in {"ascending", "descending", "asc", "desc"}:
            raise HTTPException(status_code=400, detail=f"Unsupported SortOrder: {direction}")
        catalog_direction = "desc" if direction.startswith("desc") else "asc"
        result.append(f"{catalog_field}:{catalog_direction}")
    return ",".join(result) or "release_date:desc"


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
        resources = list_movie_resources(row["content_id"])
        items.append(to_base_item_dto(
            row["content_id"], metadata.get(row["content_id"]), resources,
            progress=row, token=token,
        ))
    return {"Items": items, "TotalRecordCount": len(items), "StartIndex": 0}


@router.get("/Users/{user_id}/Items/Latest")
async def items_latest(user_id: str, request: Request, Limit: int = Query(16)):
    token = _require_auth(request)
    page = await _catalog_page(start_index=0, limit=Limit)
    # Latest 返回裸数组（无 Items 包装）
    return [
        to_base_item_dto(
            str(metadata.get("content_id") or metadata.get("dvd_id") or ""),
            metadata,
            token=token,
        )
        for metadata in page["data"]
    ]


@router.get("/Users/{user_id}/Items/{item_id}")
async def item_detail(user_id: str, item_id: str, request: Request):
    token = _require_auth(request)
    from modules.info_client import get_info_client

    try:
        metadata = await get_info_client().get_catalog_video(item_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Item not found")
    resources = list_movie_resources(item_id)
    progress = get_progress(item_id, source="library")
    return to_base_item_dto(item_id, metadata, resources, progress=progress, token=token, detailed=True)


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
    catalog_sort = _catalog_sort_spec(SortBy, SortOrder)
    random_seed = None
    if any(part.startswith("random:") for part in catalog_sort.split(",")):
        random_seed = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    page = await _catalog_page(
        start_index=StartIndex,
        limit=Limit,
        search_term=SearchTerm,
        sort_by=catalog_sort,
        random_seed=random_seed,
    )
    items = [
        to_base_item_dto(
            str(metadata.get("content_id") or metadata.get("dvd_id") or ""),
            metadata,
            token=token,
        )
        for metadata in page["data"]
    ]
    return {"Items": items, "TotalRecordCount": page["total_count"], "StartIndex": StartIndex}


@router.get("/Items/{item_id}/Images/Primary")
@router.get("/Items/{item_id}/Images/Primary/{index}")
async def item_primary_image(item_id: str, request: Request, index: int = 0):
    # 海报：302 到元数据封面（图片端点不少客户端不带 token，放宽鉴权只查 enabled）
    _ensure_enabled()
    from modules.info_client import get_info_client

    try:
        metadata = await get_info_client().get_catalog_video(item_id)
    except Exception:
        metadata = {}
    url = str(metadata.get("jacket_full_url") or metadata.get("jacket_thumb_url") or "")
    if not url:
        raise HTTPException(status_code=404, detail="No image")
    return RedirectResponse(url=url, status_code=302)


# ── 播放 ─────────────────────────────────────────────────────────


@router.get("/Items/{item_id}/PlaybackInfo")
@router.post("/Items/{item_id}/PlaybackInfo")
async def playback_info(item_id: str, request: Request):
    token = _require_auth(request)
    resources = [
        resource for resource in list_movie_resources(item_id)
        if resource.get("resource_type") == "video" and resource.get("status") == "ready"
    ]
    sources = [media_source_dto(resource, item_id, token=token) for resource in resources]
    sources.append(online_media_source_dto(item_id, token=token))
    return {
        "MediaSources": sources,
        "PlaySessionId": uuid.uuid4().hex,
    }


async def _resolve_online_stream(item_id: str) -> str:
    from modules.info_client import get_info_client
    from sources.m3u8_source import M3U8Source

    try:
        metadata = await get_info_client().get_catalog_video(item_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Item not found")
    search_code = str(
        metadata.get("dvd_id")
        or metadata.get("canonical_number")
        or metadata.get("content_id")
        or item_id
    )
    result, _attempts = await M3U8Source().search_m3u8(search_code)
    if not result or not result.get("m3u8_url"):
        raise HTTPException(status_code=404, detail="No online playback source")
    return f"/api/v1/stream/proxy?url={quote(str(result['m3u8_url']), safe='')}"


@router.get("/Videos/{item_id}/stream")
@router.get("/Videos/{item_id}/stream.{ext}")
async def video_stream(
    item_id: str,
    request: Request,
    ext: str = "",
    MediaSourceId: Optional[str] = Query(None),
    mode: str = Query(""),
):
    """Emby stream entry; 115 resolution happens only for this final request."""
    _require_auth(request)
    if MediaSourceId == "online:auto":
        return RedirectResponse(url=await _resolve_online_stream(item_id), status_code=302)

    resource = None
    if MediaSourceId and MediaSourceId.startswith("open115:"):
        try:
            resource_id = int(MediaSourceId.split(":", 1)[1])
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Media source not found") from exc
        resource = get_movie_resource(resource_id)
    else:
        resources = [
            item for item in list_movie_resources(item_id)
            if item.get("resource_type") == "video" and item.get("status") == "ready"
        ]
        resource = next((item for item in resources if item.get("is_default")), None)
        resource = resource or (resources[0] if resources else None)

    if not resource or str(resource.get("movie_id")) != item_id:
        raise HTTPException(status_code=404, detail="Media source not found")

    requested_mode = mode or ("hls" if ext.lower() == "m3u8" else "original")
    from routers.playback import stream_movie_resource

    return await stream_movie_resource(
        int(resource["id"]),
        request,
        mode=requested_mode,
        caller="emby",
    )


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
