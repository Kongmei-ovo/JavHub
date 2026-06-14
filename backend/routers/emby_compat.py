"""Emby 兼容 API 最小子集（Infuse / VidHub / SenPlayer 直连）。

实现依据：Jellyfin OpenAPI（https://api.jellyfin.org）与客户端抓包；
不参考任何 GPL 实现。原则：
- 未实现端点返回 200 + 空集合（empty_result），绝不 404 —— 兼容层稳定性关键。
- /Videos/{id}/stream 是唯一视频出口：经 StorageResolver 实时换链后 302，
  直链永不缓存/落库（即 CMS 302 服务的替代品）。
- 进度与 Web 端共表（playback_progress, source='library'），互通续播。

路由同时挂根路径与 /emby 前缀（main.py 注册两次）。
反代注意：Nginx 需把 /emby、/Users、/System、/Videos、/Items、/Sessions、/Shows
转发到后端（见 docs/emby-compat.md）。
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import uuid
from typing import Any, Optional
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.params import Query as QueryParam
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from config import config
from database import (
    get_movie_resource,
    get_progress,
    get_progress_map,
    list_movie_resources,
    list_continue_watching,
    save_progress,
)
from services.emby_mapper import (
    SERVER_ID,
    empty_result,
    library_view_dto,
    ticks_to_seconds,
    to_base_item_dto,
)
from services.emby_images import (
    actress_image_url,
    movie_backdrop_image_urls,
    movie_primary_image_url,
)
from services.emby_playback import emby_playback_broker
from services.emby_auth import (
    EmbyHTTPException,
    extract_token,
    issue_token,
    remember_session,
    require_auth,
)
from services.emby_catalog import (
    group_movie_cards,
    parse_person_id,
    person_dto,
    sort_grouped_movies,
    split_csv,
)
from services.emby_protocol import (
    display_preferences as display_preferences_payload,
    localization_cultures,
    public_server_configuration,
    server_configuration,
    startup_configuration,
    system_info as system_info_payload,
)
from services.emby_state import (
    is_movie_favorite,
    mark_movie_played,
    movie_favorite_flags,
    select_state_movie_ids,
    set_movie_favorite,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["emby-compat"])
discovery_router = APIRouter(tags=["emby-compat"])

EMBY_USER_ID = "javhub-emby-user"
METADATA_CONCURRENCY = 8
EMBY_FIELDS_REQUIRING_DETAIL = {
    "backdropimagetags",
    "genres",
    "genreitems",
    "overview",
    "people",
    "seriesname",
    "studios",
}
TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


# ── 鉴权 ─────────────────────────────────────────────────────────


def _ensure_enabled() -> None:
    if not config.emby_compat_enabled:
        raise HTTPException(status_code=403, detail="Emby compat API is disabled")


def _extract_token(request: Request) -> str:
    return extract_token(request)


def _require_auth(request: Request) -> str:
    _ensure_enabled()
    return require_auth(
        request,
        config.emby_compat_username,
        config.emby_compat_password,
    )


def _user_dto() -> dict:
    return {
        "Id": EMBY_USER_ID,
        "ServerId": SERVER_ID,
        "Name": config.emby_compat_username,
        "HasPassword": True,
        "HasConfiguredPassword": True,
        "HasConfiguredEasyPassword": False,
        "EnableAutoLogin": False,
        "Policy": {
            "IsAdministrator": False,
            "IsHidden": False,
            "IsDisabled": False,
            "EnableUserPreferenceAccess": True,
            "EnableRemoteAccess": True,
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "EnableLiveTvAccess": False,
            "EnableContentDownloading": False,
            "EnableAllChannels": True,
            "EnableAllFolders": True,
            "EnableAllDevices": True,
        },
        "Configuration": {
            "PlayDefaultAudioTrack": True,
            "DisplayCollectionsView": True,
            "DisplayMissingEpisodes": False,
            "SubtitleMode": "Default",
            "EnableNextEpisodeAutoPlay": False,
            "AudioLanguagePreference": "",
            "SubtitleLanguagePreference": "",
        },
    }


# ── 元数据辅助 ───────────────────────────────────────────────────


async def _metadata_for(codes: list[str]) -> dict[str, Optional[dict]]:
    from modules.info_client import get_info_client

    client = get_info_client()
    sem = asyncio.Semaphore(METADATA_CONCURRENCY)

    async def fetch(code: str):
        async with sem:
            try:
                return code, await client.get_catalog_video(code)
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


def _query_value(request: Request, *names: str, default: Any = None) -> Any:
    query = getattr(request, "query_params", {}) or {}
    lowered = {str(key).casefold(): value for key, value in query.items()}
    for name in names:
        value = lowered.get(name.casefold())
        if value is not None:
            return value
    return default


def _query_int(request: Request, *names: str, default: int) -> int:
    try:
        return int(_query_value(request, *names, default=default))
    except (TypeError, ValueError):
        return default


# ── 认证与系统信息 ───────────────────────────────────────────────


async def _authentication_values(request: Request) -> dict[str, str]:
    values: dict[str, Any] = {}
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            values.update(payload)
    except Exception:
        try:
            raw = (await request.body()).decode("utf-8", errors="replace")
            values.update({key: parts[-1] for key, parts in parse_qs(raw).items() if parts})
        except Exception:
            pass
    query = getattr(request, "query_params", {}) or {}
    for key, value in query.items():
        values.setdefault(key, value)
    return {str(key).casefold(): str(value) for key, value in values.items()}


@discovery_router.api_route("", methods=["GET", "HEAD"], include_in_schema=False)
@discovery_router.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def emby_root(request: Request):
    _ensure_enabled()
    return system_info_payload(request)


@router.post("/Users/AuthenticateByName")
@router.post("/Users/authenticatebyname", include_in_schema=False)
@router.post("/users/AuthenticateByName", include_in_schema=False)
@router.post("/users/authenticatebyname", include_in_schema=False)
async def authenticate_by_name(request: Request):
    _ensure_enabled()
    values = await _authentication_values(request)
    username = values.get("username") or values.get("name") or values.get("loginname") or ""
    password = values.get("pw") or values.get("password") or values.get("pass") or values.get("pwd") or ""
    if not password and (values.get("passwordmd5") or values.get("passwordsha1")):
        raise EmbyHTTPException(400, "Plain password required")
    expected_username = config.emby_compat_username
    expected_password = config.emby_compat_password
    if (
        not expected_password
        or username.casefold() != expected_username.casefold()
        or password != expected_password
    ):
        raise EmbyHTTPException(401, "Invalid username or password", code=40101)
    token = issue_token(expected_username, expected_password)
    remember_session(request, token)
    headers = getattr(request, "headers", {}) or {}
    return {
        "User": _user_dto(),
        "SessionInfo": {
            "Id": uuid.uuid4().hex,
            "UserId": EMBY_USER_ID,
            "UserName": expected_username,
            "Client": headers.get("X-Emby-Client", ""),
            "DeviceId": headers.get("X-Emby-Device-Id", ""),
            "DeviceName": headers.get("X-Emby-Device-Name", ""),
        },
        "AccessToken": token,
        "ServerId": SERVER_ID,
    }


@router.api_route("/System/Info/Public", methods=["GET", "HEAD"])
@router.api_route("/system/info/public", methods=["GET", "HEAD"], include_in_schema=False)
async def system_info_public(request: Request):
    _ensure_enabled()
    return system_info_payload(request)


@router.api_route("/System/Info", methods=["GET", "HEAD"])
@router.api_route("/system/info", methods=["GET", "HEAD"], include_in_schema=False)
async def system_info(request: Request):
    _ensure_enabled()
    return system_info_payload(request, full=True)


@router.get("/System/Endpoint")
@router.get("/system/endpoint", include_in_schema=False)
async def system_endpoint():
    _ensure_enabled()
    return {"IsLocal": True, "IsInNetwork": True}


@router.api_route("/System/Ping", methods=["GET", "HEAD", "POST"])
@router.api_route("/system/ping", methods=["GET", "HEAD", "POST"], include_in_schema=False)
async def system_ping():
    _ensure_enabled()
    return PlainTextResponse("Emby Server")


@router.api_route("/System/Configuration/Public", methods=["GET", "HEAD"])
@router.api_route("/system/configuration/public", methods=["GET", "HEAD"], include_in_schema=False)
async def system_configuration_public():
    _ensure_enabled()
    return public_server_configuration()


@router.api_route("/Startup/Configuration", methods=["GET", "HEAD"])
@router.api_route("/startup/configuration", methods=["GET", "HEAD"], include_in_schema=False)
async def startup_config():
    _ensure_enabled()
    return startup_configuration()


@router.post("/Startup/Complete")
@router.post("/startup/complete", include_in_schema=False)
async def startup_complete():
    _ensure_enabled()
    return Response(status_code=204)


@router.api_route("/QuickConnect/Enabled", methods=["GET", "HEAD"])
@router.api_route("/quickconnect/enabled", methods=["GET", "HEAD"], include_in_schema=False)
async def quick_connect_enabled():
    _ensure_enabled()
    return False


@router.get("/Users/Public")
@router.get("/users/public", include_in_schema=False)
async def public_users():
    _ensure_enabled()
    user = _user_dto()
    return [{
        "Id": user["Id"],
        "Name": user["Name"],
        "ServerId": user["ServerId"],
        "HasPassword": True,
    }]


@router.get("/Branding/Configuration")
@router.get("/branding/configuration", include_in_schema=False)
async def branding(request: Request):
    _ensure_enabled()
    return {"LoginDisclaimer": "", "CustomCss": "", "SplashscreenEnabled": False}


@router.api_route("/Branding/Css", methods=["GET", "HEAD"])
@router.api_route("/branding/css", methods=["GET", "HEAD"], include_in_schema=False)
async def branding_css():
    _ensure_enabled()
    return Response(content=b"", media_type="text/css")


@router.get("/Localization/Options")
@router.get("/localization/options", include_in_schema=False)
async def localization_options():
    _ensure_enabled()
    return [{"Name": "简体中文", "Value": "zh-CN"}, {"Name": "English", "Value": "en-US"}]


@router.get("/Localization/Cultures")
@router.get("/Localization/cultures", include_in_schema=False)
@router.get("/localization/cultures", include_in_schema=False)
async def cultures():
    _ensure_enabled()
    return localization_cultures()


@router.api_route("/CustomCssJS/Scripts", methods=["GET", "HEAD"])
@router.api_route("/customcssjs/scripts", methods=["GET", "HEAD"], include_in_schema=False)
async def custom_css_scripts():
    _ensure_enabled()
    return Response(content=b"", media_type="application/javascript")


@router.post("/Sessions/Capabilities")
@router.post("/Sessions/Capabilities/Full")
@router.post("/sessions/capabilities", include_in_schema=False)
@router.post("/sessions/capabilities/full", include_in_schema=False)
async def public_session_capabilities():
    _ensure_enabled()
    return Response(status_code=204)


@router.post("/Sessions/Logout")
@router.post("/sessions/logout", include_in_schema=False)
async def session_logout():
    _ensure_enabled()
    return Response(status_code=204)


@router.get("/DisplayPreferences/{pref_id}")
@router.get("/displaypreferences/{pref_id}", include_in_schema=False)
async def display_preferences(pref_id: str):
    _ensure_enabled()
    return display_preferences_payload(pref_id)


@router.post("/DisplayPreferences/{pref_id}")
@router.post("/displaypreferences/{pref_id}", include_in_schema=False)
async def save_display_preferences(pref_id: str):
    _ensure_enabled()
    return Response(status_code=204)


@router.api_route("/embywebsocket", methods=["GET", "HEAD"])
@router.api_route(
    "/EmbyWebSocket",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def emby_websocket_probe():
    _ensure_enabled()
    return Response(status_code=204)


@router.websocket("/embywebsocket")
@router.websocket("/EmbyWebSocket")
async def emby_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        return


@router.get("/Users/Me")
@router.get("/users/me", include_in_schema=False)
async def get_me(request: Request):
    _require_auth(request)
    return _user_dto()


@router.get("/Users")
@router.get("/users", include_in_schema=False)
async def list_users(request: Request):
    _require_auth(request)
    return [_user_dto()]


@router.get("/Users/{user_id}")
@router.get("/users/{user_id}", include_in_schema=False)
async def get_user(user_id: str, request: Request):
    _require_auth(request)
    return _user_dto()


# ── 媒体库浏览 ───────────────────────────────────────────────────


@router.get("/Users/{user_id}/Views")
@router.get("/users/{user_id}/views", include_in_schema=False)
async def user_views(user_id: str, request: Request):
    _require_auth(request)
    return {"Items": [library_view_dto()], "TotalRecordCount": 1, "StartIndex": 0}


@router.get("/UserViews")
@router.get("/userviews", include_in_schema=False)
async def user_views_alias(request: Request):
    return await user_views(EMBY_USER_ID, request)


@router.get("/Library/MediaFolders")
@router.get("/library/mediafolders", include_in_schema=False)
async def media_folders(request: Request):
    return await user_views(EMBY_USER_ID, request)


@router.get("/Library/VirtualFolders")
@router.get("/Library/SelectableMediaFolders")
@router.get("/library/virtualfolders", include_in_schema=False)
@router.get("/library/selectablemediafolders", include_in_schema=False)
async def virtual_folders(request: Request):
    _require_auth(request)
    view = library_view_dto()
    return [{
        "Name": view["Name"],
        "Locations": [],
        "CollectionType": "movies",
        "ItemId": view["Id"],
        "Id": view["Id"],
        "PrimaryImageItemId": view["Id"],
        "RefreshStatus": "Idle",
        "LibraryOptions": {},
    }]


@router.get("/Users/{user_id}/Items/Resume")
@router.get("/users/{user_id}/items/resume", include_in_schema=False)
async def items_resume(user_id: str, request: Request, Limit: int = Query(12)):
    _require_auth(request)
    default_limit = 12 if isinstance(Limit, QueryParam) else Limit
    limit = min(max(_query_int(request, "Limit", default=default_limit), 1), 200)
    rows = [r for r in list_continue_watching(limit=limit) if r.get("source") == "library"]
    codes = [r["content_id"] for r in rows]
    metadata = await _metadata_for(codes) if codes else {}
    favorite_flags = await asyncio.to_thread(movie_favorite_flags, codes)
    items = []
    for row in rows:
        items.append(to_base_item_dto(
            row["content_id"],
            metadata.get(row["content_id"]),
            progress=row,
            is_favorite=favorite_flags.get(row["content_id"], False),
        ))
    return {"Items": items, "TotalRecordCount": len(items), "StartIndex": 0}


@router.get("/Users/{user_id}/Items/Latest")
@router.get("/users/{user_id}/items/latest", include_in_schema=False)
async def items_latest(user_id: str, request: Request, Limit: int = Query(16)):
    _require_auth(request)
    default_limit = 16 if isinstance(Limit, QueryParam) else Limit
    limit = min(max(_query_int(request, "Limit", default=default_limit), 1), 200)
    page = await _catalog_page(start_index=0, limit=limit)
    # Latest 返回裸数组（无 Items 包装）
    rows = group_movie_cards(list(page["data"]))[:limit]
    content_ids = [
        str(metadata.get("content_id") or metadata.get("dvd_id") or "")
        for metadata in rows
    ]
    progress_map, favorite_flags = await asyncio.gather(
        asyncio.to_thread(get_progress_map, content_ids, source="library"),
        asyncio.to_thread(movie_favorite_flags, content_ids),
    )
    return [
        to_base_item_dto(
            str(metadata.get("content_id") or metadata.get("dvd_id") or ""),
            metadata,
            progress=progress_map.get(
                str(metadata.get("content_id") or metadata.get("dvd_id") or "")
            ),
            is_favorite=favorite_flags.get(
                str(metadata.get("content_id") or metadata.get("dvd_id") or ""),
                False,
            ),
        )
        for metadata in rows
    ]


@router.get("/Items/Resume")
@router.get("/items/resume", include_in_schema=False)
async def items_resume_alias(request: Request, Limit: int = Query(12)):
    return await items_resume(EMBY_USER_ID, request, Limit)


@router.get("/Items/Latest")
@router.get("/items/latest", include_in_schema=False)
async def items_latest_alias(request: Request, Limit: int = Query(16)):
    return await items_latest(EMBY_USER_ID, request, Limit)


@router.get("/Items/Counts")
@router.get("/Users/{user_id}/Items/Counts")
@router.get("/items/counts", include_in_schema=False)
@router.get("/users/{user_id}/items/counts", include_in_schema=False)
async def items_counts(request: Request, user_id: str = ""):
    _require_auth(request)
    from modules.info_client import get_info_client

    page = await get_info_client().list_catalog_videos(
        page=1,
        page_size=1,
        sort_by="release_date:desc",
        random_seed=None,
        include_total=True,
    )
    return {
        "MovieCount": int(page.get("total_count") or 0),
        "SeriesCount": 0,
        "EpisodeCount": 0,
        "ArtistCount": 0,
        "AlbumCount": 0,
        "SongCount": 0,
        "MusicVideoCount": 0,
        "BookCount": 0,
        "BoxSetCount": 0,
    }


@router.get("/Persons")
@router.get("/persons", include_in_schema=False)
async def persons(request: Request):
    _require_auth(request)
    from modules.info_client import get_info_client

    start_index = max(_query_int(request, "StartIndex", default=0), 0)
    limit = min(max(_query_int(request, "Limit", default=50), 1), 100)
    search_term = str(_query_value(request, "SearchTerm", default="") or "")
    page = start_index // limit + 1
    offset = start_index % limit
    result = await get_info_client().list_actresses(
        q=search_term or None,
        page=page,
        page_size=limit,
    )
    rows = list(result.get("data") or [])[offset:offset + limit]
    return {
        "Items": [person_dto(row) for row in rows],
        "TotalRecordCount": int(result.get("total_count") or len(rows)),
        "StartIndex": start_index,
    }


async def _person_movies_page(
    person_ids: str,
    *,
    start_index: int,
    limit: int,
    sort_by: str,
    sort_order: str,
) -> dict:
    from modules.info_client import get_info_client

    actress_ids = list(
        dict.fromkeys(
            value
            for value in (parse_person_id(item) for item in split_csv(person_ids))
            if value is not None
        )
    )
    if not actress_ids:
        return {"data": [], "total_count": 0}

    results = await asyncio.gather(
        *(
            get_info_client().get_all_actress_videos(
                actress_id,
                include_supplement="resolved",
                include_total=True,
            )
            for actress_id in actress_ids
        )
    )
    rows: list[dict[str, Any]] = []
    for result in results:
        rows.extend(result.get("data") or [])
    grouped = group_movie_cards(rows)
    grouped = sort_grouped_movies(grouped, sort_by, sort_order)
    return {
        "data": grouped[start_index:start_index + limit],
        "total_count": len(grouped),
    }


async def _state_movies_page(
    filters: str,
    *,
    start_index: int,
    limit: int,
    sort_by: str,
    sort_order: str,
) -> dict | None:
    movie_ids = await asyncio.to_thread(
        select_state_movie_ids,
        filters,
        sort_by,
        sort_order,
    )
    if movie_ids is None:
        return None
    selected = movie_ids[start_index:start_index + limit]
    from modules.info_client import get_info_client

    details = await asyncio.gather(
        *(get_info_client().get_catalog_video(movie_id) for movie_id in selected),
        return_exceptions=True,
    )
    return {
        "data": group_movie_cards([
            detail for detail in details
            if isinstance(detail, dict)
        ]),
        "total_count": len(movie_ids),
    }


async def _browse_items_impl(
    *,
    request: Request,
    parent_id: str | None,
    start_index: int,
    limit: int,
    sort_by: str,
    sort_order: str,
    search_term: str | None,
    include_item_types: str = "",
    ids: str = "",
    filters: str = "",
    person_ids: str = "",
) -> dict:
    token = _require_auth(request)
    item_types = {item.casefold() for item in split_csv(include_item_types)}
    supported = {"movie", "video", "folder", "collectionfolder"}
    if item_types and not item_types.intersection(supported):
        return {"Items": [], "TotalRecordCount": 0, "StartIndex": start_index}
    if item_types and item_types.issubset({"folder", "collectionfolder"}) and not parent_id:
        return await user_views(EMBY_USER_ID, request)
    if (
        parent_id
        and parent_id.casefold() != "library"
        and not ids
        and not person_ids
    ):
        return {"Items": [], "TotalRecordCount": 0, "StartIndex": start_index}

    from modules.info_client import get_info_client

    if ids:
        catalog_ids = split_csv(ids)
        details = await asyncio.gather(
            *(get_info_client().get_catalog_video(item_id) for item_id in catalog_ids),
            return_exceptions=True,
        )
        rows = [
            detail for detail in details
            if isinstance(detail, dict)
        ]
        page = {"data": group_movie_cards(rows), "total_count": len(rows)}
    elif person_ids:
        page = await _person_movies_page(
            person_ids,
            start_index=start_index,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        start_index = 0
    else:
        page = await _state_movies_page(
            filters,
            start_index=start_index,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        if page is None:
            catalog_sort = _catalog_sort_spec(sort_by, sort_order)
            random_seed = None
            if any(part.startswith("random:") for part in catalog_sort.split(",")):
                random_seed = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            page = await _catalog_page(
                start_index=start_index,
                limit=limit,
                search_term=search_term,
                sort_by=catalog_sort,
                random_seed=random_seed,
            )
            page["data"] = group_movie_cards(list(page.get("data") or []))

    content_ids = [
        str(metadata.get("content_id") or metadata.get("dvd_id") or "")
        for metadata in page.get("data") or []
    ]
    requested_fields = {
        field.casefold()
        for field in split_csv(_query_value(request, "Fields", default=""))
    }
    if requested_fields.intersection(EMBY_FIELDS_REQUIRING_DETAIL):
        detail_map = await _metadata_for(content_ids)
        page["data"] = [
            detail_map.get(content_id) or metadata
            for content_id, metadata in zip(content_ids, page.get("data") or [])
        ]
    progress_map, favorite_flags = await asyncio.gather(
        asyncio.to_thread(get_progress_map, content_ids, source="library"),
        asyncio.to_thread(movie_favorite_flags, content_ids),
    )
    items = [
        to_base_item_dto(
            content_id,
            metadata,
            progress=progress_map.get(content_id),
            is_favorite=favorite_flags.get(content_id, False),
        )
        for content_id, metadata in zip(content_ids, page.get("data") or [])
    ]
    return {
        "Items": items,
        "TotalRecordCount": int(page.get("total_count") or 0),
        "StartIndex": start_index,
    }


@router.get("/Users/{user_id}/Items/{item_id}")
@router.get("/users/{user_id}/items/{item_id}", include_in_schema=False)
async def item_detail(user_id: str, item_id: str, request: Request):
    _require_auth(request)
    from modules.info_client import get_info_client

    try:
        metadata = await get_info_client().get_catalog_video(item_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Item not found")
    progress = get_progress(item_id, source="library")
    favorite = await asyncio.to_thread(is_movie_favorite, item_id)
    return to_base_item_dto(
        item_id,
        metadata,
        progress=progress,
        is_favorite=favorite,
    )


@router.get("/Items/{item_id}")
@router.get("/items/{item_id}", include_in_schema=False)
async def generic_item_detail(item_id: str, request: Request):
    _require_auth(request)
    if item_id.casefold().startswith("person:"):
        actress_id = parse_person_id(item_id)
        if actress_id is None:
            raise EmbyHTTPException(404, "Item not found")
        from modules.info_client import get_info_client

        try:
            actress = await get_info_client().get_actress(actress_id)
        except Exception as exc:
            raise EmbyHTTPException(404, "Item not found") from exc
        return person_dto(actress, detailed=True)
    return await item_detail(EMBY_USER_ID, item_id, request)


@router.get("/Users/{user_id}/Items")
@router.get("/users/{user_id}/items", include_in_schema=False)
async def items_browse(
    user_id: str,
    request: Request,
    ParentId: Optional[str] = Query(None),
    StartIndex: int = Query(0, ge=0),
    Limit: int = Query(50, ge=1, le=200),
    SortBy: str = Query("DateCreated"),
    SortOrder: str = Query("Descending"),
    SearchTerm: Optional[str] = Query(None),
    IncludeItemTypes: str = Query(""),
    Ids: str = Query(""),
    Filters: str = Query(""),
    PersonIds: str = Query(""),
):
    parent_default = None if isinstance(ParentId, QueryParam) else ParentId
    start_default = 0 if isinstance(StartIndex, QueryParam) else StartIndex
    limit_default = 50 if isinstance(Limit, QueryParam) else Limit
    sort_default = "DateCreated" if isinstance(SortBy, QueryParam) else SortBy
    order_default = "Descending" if isinstance(SortOrder, QueryParam) else SortOrder
    search_default = None if isinstance(SearchTerm, QueryParam) else SearchTerm
    types_default = "" if isinstance(IncludeItemTypes, QueryParam) else IncludeItemTypes
    ids_default = "" if isinstance(Ids, QueryParam) else Ids
    filters_default = "" if isinstance(Filters, QueryParam) else Filters
    people_default = "" if isinstance(PersonIds, QueryParam) else PersonIds
    return await _browse_items_impl(
        request=request,
        parent_id=_query_value(request, "ParentId", default=parent_default),
        start_index=max(_query_int(request, "StartIndex", default=start_default), 0),
        limit=min(max(_query_int(request, "Limit", default=limit_default), 1), 200),
        sort_by=str(_query_value(request, "SortBy", default=sort_default) or "DateCreated"),
        sort_order=str(
            _query_value(request, "SortOrder", default=order_default) or "Descending"
        ),
        search_term=_query_value(request, "SearchTerm", default=search_default),
        include_item_types=str(
            _query_value(request, "IncludeItemTypes", default=types_default) or ""
        ),
        ids=str(_query_value(request, "Ids", default=ids_default) or ""),
        filters=str(_query_value(request, "Filters", default=filters_default) or ""),
        person_ids=str(_query_value(request, "PersonIds", default=people_default) or ""),
    )


@router.get("/Items")
@router.get("/items", include_in_schema=False)
async def generic_items(request: Request):
    return await _browse_items_impl(
        request=request,
        parent_id=_query_value(request, "ParentId"),
        start_index=max(_query_int(request, "StartIndex", default=0), 0),
        limit=min(max(_query_int(request, "Limit", default=50), 1), 200),
        sort_by=str(_query_value(request, "SortBy", default="DateCreated") or "DateCreated"),
        sort_order=str(_query_value(request, "SortOrder", default="Descending") or "Descending"),
        search_term=_query_value(request, "SearchTerm"),
        include_item_types=str(_query_value(request, "IncludeItemTypes", default="") or ""),
        ids=str(_query_value(request, "Ids", default="") or ""),
        filters=str(_query_value(request, "Filters", default="") or ""),
        person_ids=str(_query_value(request, "PersonIds", default="") or ""),
    )


@router.api_route("/Items/{item_id}/Images/{image_type}", methods=["GET", "HEAD"])
@router.api_route("/Items/{item_id}/Images/{image_type}/{index}", methods=["GET", "HEAD"])
@router.api_route(
    "/items/{item_id}/images/{image_type}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@router.api_route(
    "/items/{item_id}/images/{image_type}/{index}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def item_image(
    item_id: str,
    image_type: str,
    request: Request,
    index: int = 0,
):
    # Image probes often omit auth, so enabled state is the only gate.
    _ensure_enabled()
    from modules.info_client import get_info_client

    url = ""
    if item_id.casefold().startswith("person:"):
        if image_type.casefold() == "primary":
            actress_id = parse_person_id(item_id)
        else:
            actress_id = None
        if actress_id is not None:
            try:
                actress = await get_info_client().get_actress(actress_id)
            except Exception:
                actress = {}
            url = actress_image_url(actress)
    else:
        try:
            metadata = await get_info_client().get_catalog_video(item_id)
        except Exception:
            metadata = {}
        image_kind = image_type.casefold()
        if image_kind == "primary":
            url = movie_primary_image_url(metadata)
        elif image_kind == "backdrop":
            candidates = movie_backdrop_image_urls(metadata)
            if 0 <= index < len(candidates):
                url = candidates[index]
    if not url:
        return Response(
            content=b"" if request.method == "HEAD" else TRANSPARENT_PNG,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"},
        )
    return RedirectResponse(
        url=url,
        status_code=302,
        headers={"Cache-Control": "public, max-age=300"},
    )


# ── 播放 ─────────────────────────────────────────────────────────


@router.get("/Items/{item_id}/PlaybackInfo")
@router.post("/Items/{item_id}/PlaybackInfo")
@router.get("/items/{item_id}/playbackinfo", include_in_schema=False)
@router.post("/items/{item_id}/playbackinfo", include_in_schema=False)
async def playback_info(item_id: str, request: Request):
    token = _require_auth(request)
    sources = emby_playback_broker.describe(
        item_id,
        token,
        list_movie_resources(item_id),
    )
    return {
        "MediaSources": sources,
        "PlaySessionId": uuid.uuid4().hex,
    }


@router.get("/Users/{user_id}/Items/{item_id}/PlaybackInfo")
@router.post("/Users/{user_id}/Items/{item_id}/PlaybackInfo")
@router.get("/users/{user_id}/items/{item_id}/playbackinfo", include_in_schema=False)
@router.post("/users/{user_id}/items/{item_id}/playbackinfo", include_in_schema=False)
async def user_playback_info(user_id: str, item_id: str, request: Request):
    return await playback_info(item_id, request)


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


@router.api_route("/Videos/{item_id}/stream", methods=["GET", "HEAD"])
@router.api_route("/Videos/{item_id}/stream.{ext}", methods=["GET", "HEAD"])
@router.api_route(
    "/videos/{item_id}/stream",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@router.api_route(
    "/videos/{item_id}/stream.{ext}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def video_stream(
    item_id: str,
    request: Request,
    ext: str = "",
    MediaSourceId: Optional[str] = Query(None),
    mode: str = Query(""),
):
    """Emby stream entry; 115 resolution happens only for this final request."""
    _require_auth(request)
    if getattr(request, "method", "GET").upper() == "HEAD":
        return Response(
            status_code=200,
            media_type=emby_playback_broker.probe_media_type(ext),
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
            },
        )

    media_source_id = (
        None if isinstance(MediaSourceId, QueryParam) else MediaSourceId
    ) or _query_value(request, "MediaSourceId")
    requested_mode_value = (
        "" if isinstance(mode, QueryParam) else mode
    )
    selection = emby_playback_broker.select(
        item_id,
        str(media_source_id or ""),
        get_resource=get_movie_resource,
        list_resources=list_movie_resources,
    )
    if selection is None:
        raise HTTPException(status_code=404, detail="Media source not found")
    if selection.kind == "online":
        return RedirectResponse(url=await _resolve_online_stream(item_id), status_code=302)

    resource = selection.resource or {}
    requested_mode = requested_mode_value or ("hls" if ext.lower() == "m3u8" else "original")
    from routers.playback import stream_movie_resource

    return await stream_movie_resource(
        int(resource["id"]),
        request,
        mode=requested_mode,
        caller="emby",
    )


@router.api_route("/Videos/{item_id}/original", methods=["GET", "HEAD"])
@router.api_route("/Videos/{item_id}/original.{ext}", methods=["GET", "HEAD"])
@router.api_route(
    "/videos/{item_id}/original",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@router.api_route(
    "/videos/{item_id}/original.{ext}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def video_original(item_id: str, request: Request, ext: str = ""):
    return await video_stream(
        item_id,
        request,
        ext=ext,
        MediaSourceId=_query_value(request, "MediaSourceId"),
        mode="original",
    )


@router.api_route("/Videos/{item_id}/master.m3u8", methods=["GET", "HEAD"])
@router.api_route("/Videos/{item_id}/main.m3u8", methods=["GET", "HEAD"])
@router.api_route(
    "/videos/{item_id}/master.m3u8",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@router.api_route(
    "/videos/{item_id}/main.m3u8",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def video_hls(item_id: str, request: Request):
    return await video_stream(
        item_id,
        request,
        ext="m3u8",
        MediaSourceId=_query_value(request, "MediaSourceId"),
        mode="hls",
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
@router.post("/sessions/playing", include_in_schema=False)
async def session_playing(request: Request):
    return await _record_session_progress(request)


@router.post("/Sessions/Playing/Progress")
@router.post("/sessions/playing/progress", include_in_schema=False)
async def session_progress(request: Request):
    return await _record_session_progress(request)


@router.post("/Sessions/Playing/Stopped")
@router.post("/sessions/playing/stopped", include_in_schema=False)
async def session_stopped(request: Request):
    return await _record_session_progress(request)


@router.post("/Users/{user_id}/FavoriteItems/{item_id}")
@router.post("/users/{user_id}/favoriteitems/{item_id}", include_in_schema=False)
async def favorite_item(user_id: str, item_id: str, request: Request):
    _require_auth(request)
    await asyncio.to_thread(set_movie_favorite, item_id, True)
    return {"Id": item_id, "IsFavorite": True}


@router.delete("/Users/{user_id}/FavoriteItems/{item_id}")
@router.delete("/users/{user_id}/favoriteitems/{item_id}", include_in_schema=False)
async def unfavorite_item(user_id: str, item_id: str, request: Request):
    _require_auth(request)
    await asyncio.to_thread(set_movie_favorite, item_id, False)
    return {"Id": item_id, "IsFavorite": False}


@router.post("/Users/{user_id}/PlayedItems/{item_id}")
@router.post("/users/{user_id}/playeditems/{item_id}", include_in_schema=False)
async def played_item(user_id: str, item_id: str, request: Request):
    _require_auth(request)
    await asyncio.to_thread(mark_movie_played, item_id, True)
    return {"Id": item_id, "Played": True}


@router.delete("/Users/{user_id}/PlayedItems/{item_id}")
@router.delete("/users/{user_id}/playeditems/{item_id}", include_in_schema=False)
async def unplayed_item(user_id: str, item_id: str, request: Request):
    _require_auth(request)
    await asyncio.to_thread(mark_movie_played, item_id, False)
    return {"Id": item_id, "Played": False}


# ── 未实现端点：200 + 空集合（绝不 404）──────────────────────────

EMPTY_COLLECTION_PATHS = (
    "/Shows/NextUp",
    "/Shows/Upcoming",
    "/Artists",
    "/Genres",
    "/Items/Filters",
    "/Items/Filters2",
    "/Users/{user_id}/Items/Suggestions",
    "/Movies/Recommendations",
)

for _path in EMPTY_COLLECTION_PATHS:
    async def _empty_endpoint(request: Request, user_id: str = ""):
        _require_auth(request)
        return empty_result()

    router.add_api_route(_path, _empty_endpoint, methods=["GET"], include_in_schema=False)


@router.get("/Sessions")
@router.get("/sessions", include_in_schema=False)
async def sessions(request: Request):
    _require_auth(request)
    return []


@router.get("/System/Configuration")
@router.get("/system/configuration", include_in_schema=False)
async def private_system_configuration(request: Request):
    _require_auth(request)
    return server_configuration()


@router.api_route("/System/Ext/ServerDomains", methods=["GET", "HEAD"])
@router.api_route(
    "/system/ext/serverdomains",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def server_domains():
    _ensure_enabled()
    return []


@router.post("/Users/{user_id}/Configuration")
@router.post("/users/{user_id}/configuration", include_in_schema=False)
async def save_user_configuration(user_id: str, request: Request):
    _require_auth(request)
    return Response(status_code=204)


@router.get("/System/WakeOnLanInfo")
@router.get("/system/wakeonlaninfo", include_in_schema=False)
@router.get("/ScheduledTasks")
@router.get("/scheduledtasks", include_in_schema=False)
@router.get("/Web/ConfigurationPages")
@router.get("/web/configurationpages", include_in_schema=False)
async def empty_array_probe(request: Request):
    _require_auth(request)
    return []


@router.get("/LiveTv/Recordings")
@router.get("/livetv/recordings", include_in_schema=False)
@router.get("/System/ActivityLog/Entries")
@router.get("/system/activitylog/entries", include_in_schema=False)
async def empty_items_probe(request: Request):
    _require_auth(request)
    return empty_result()


@router.get("/Items/{item_id}/Similar")
@router.get("/items/{item_id}/similar", include_in_schema=False)
@router.get("/Items/{item_id}/ThumbnailSet")
@router.get("/items/{item_id}/thumbnailset", include_in_schema=False)
@router.get("/Items/{item_id}/SpecialFeatures")
@router.get("/items/{item_id}/specialfeatures", include_in_schema=False)
@router.get("/Items/{item_id}/Intros")
@router.get("/items/{item_id}/intros", include_in_schema=False)
@router.get("/Users/{user_id}/Items/{item_id}/SpecialFeatures")
@router.get(
    "/users/{user_id}/items/{item_id}/specialfeatures",
    include_in_schema=False,
)
@router.get("/Users/{user_id}/Items/{item_id}/Intros")
@router.get(
    "/users/{user_id}/items/{item_id}/intros",
    include_in_schema=False,
)
async def empty_item_features(
    item_id: str,
    request: Request,
    user_id: str = "",
):
    _require_auth(request)
    return empty_result()


@router.get("/Shows/{item_id}/Seasons")
@router.get("/shows/{item_id}/seasons", include_in_schema=False)
@router.get("/Shows/{item_id}/Episodes")
@router.get("/shows/{item_id}/episodes", include_in_schema=False)
@router.get("/Users/{user_id}/Shows/{item_id}/Seasons")
@router.get(
    "/users/{user_id}/shows/{item_id}/seasons",
    include_in_schema=False,
)
@router.get("/Users/{user_id}/Shows/{item_id}/Episodes")
@router.get(
    "/users/{user_id}/shows/{item_id}/episodes",
    include_in_schema=False,
)
async def empty_show_children(
    item_id: str,
    request: Request,
    user_id: str = "",
):
    _require_auth(request)
    return empty_result()


@router.get("/Users/{user_id}/Shows/NextUp")
@router.get("/users/{user_id}/shows/nextup", include_in_schema=False)
@router.get("/Users/{user_id}/Shows/Upcoming")
@router.get("/users/{user_id}/shows/upcoming", include_in_schema=False)
async def empty_user_shows(user_id: str, request: Request):
    _require_auth(request)
    return empty_result()


@router.get("/MediaSegments/{item_id}")
@router.get("/mediasegments/{item_id}", include_in_schema=False)
async def media_segments(item_id: str, request: Request):
    _require_auth(request)
    return empty_result()


@router.get("/LiveTv/Channels")
@router.get("/livetv/channels", include_in_schema=False)
@router.get("/LiveTv/Programs")
@router.get("/livetv/programs", include_in_schema=False)
@router.get("/LiveTv/Timers")
@router.get("/livetv/timers", include_in_schema=False)
@router.get("/LiveTv/SeriesTimers")
@router.get("/livetv/seriestimers", include_in_schema=False)
async def empty_livetv_collections(request: Request):
    _require_auth(request)
    return empty_result()


@router.get("/Items/{item_id}/ThemeMedia")
@router.get("/items/{item_id}/thememedia", include_in_schema=False)
async def theme_media(item_id: str, request: Request):
    _require_auth(request)
    empty = empty_result()
    return {
        "ThemeVideosResult": empty,
        "ThemeSongsResult": empty,
        "SoundtrackSongsResult": empty,
    }
