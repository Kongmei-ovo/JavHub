"""library_files + JavInfo 元数据 → Emby BaseItemDto 映射。

字段依据 Jellyfin OpenAPI（https://api.jellyfin.org）/ Emby 公开协议；
不参考任何 GPL 实现。只输出 Infuse/VidHub 实际消费的最小字段集。

时长/进度单位为 Ticks：1 tick = 100ns，秒 × 10_000_000。
"""
from __future__ import annotations

from typing import Optional

TICKS_PER_SECOND = 10_000_000
SERVER_ID = "javhub-emby-compat"
LIBRARY_VIEW_ID = "library"


def seconds_to_ticks(seconds: float | int | None) -> int:
    return int(float(seconds or 0) * TICKS_PER_SECOND)


def ticks_to_seconds(ticks: float | int | None) -> float:
    return float(ticks or 0) / TICKS_PER_SECOND


def _container_of(name: str) -> str:
    lowered = str(name or "").lower()
    return lowered.rsplit(".", 1)[-1] if "." in lowered else "mp4"


def media_source_dto(file: dict, token: str = "") -> dict:
    """library_files 行 → MediaSource。DirectStreamUrl 指向本服务的 302 出口。"""
    source_id = f"lib:{file['id']}"
    container = _container_of(file.get("name"))
    item_id = str(file.get("content_id") or "")
    stream_url = f"/Videos/{item_id}/stream.{container}?MediaSourceId={source_id}&Static=true"
    if token:
        stream_url += f"&api_key={token}"
    return {
        "Id": source_id,
        "Protocol": "Http",
        "Container": container,
        "Size": int(file.get("size") or 0),
        "Name": file.get("name") or "",
        "Path": file.get("name") or "",
        "IsRemote": False,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [],
        "RequiredHttpHeaders": {},
    }


def online_media_source_dto(item_id: str, token: str = "") -> dict:
    """按需解析的在线 HLS 版本；这里只暴露稳定入口，不缓存上游直链。"""
    stream_url = f"/Videos/{item_id}/stream.m3u8?MediaSourceId=online:auto&Static=true"
    if token:
        stream_url += f"&api_key={token}"
    return {
        "Id": "online:auto",
        "Protocol": "Http",
        "Container": "m3u8",
        "Name": "在线源（按需检测）",
        "Path": "online:auto",
        "IsRemote": True,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [],
        "RequiredHttpHeaders": {},
    }


def to_base_item_dto(
    content_id: str,
    metadata: Optional[dict],
    files: Optional[list[dict]] = None,
    progress: Optional[dict] = None,
    token: str = "",
    detailed: bool = False,
) -> dict:
    """组装 Movie 类型的 BaseItemDto。metadata 缺失时退化为番号占位。"""
    metadata = metadata or {}
    title = str(
        metadata.get("title_ja_translated")
        or metadata.get("title_ja")
        or metadata.get("title_en")
        or content_id
    )
    runtime_mins = metadata.get("runtime_mins") or 0
    release_date = str(metadata.get("release_date") or "")
    year = None
    if len(release_date) >= 4 and release_date[:4].isdigit():
        year = int(release_date[:4])

    dto: dict = {
        "Id": content_id,
        "ServerId": SERVER_ID,
        "Name": title,
        "OriginalTitle": str(metadata.get("title_ja") or title),
        "SortName": title,
        "Type": "Movie",
        "MediaType": "Video",
        "IsFolder": False,
        "LocationType": "Remote",
        "ProductionYear": year,
        "PremiereDate": f"{release_date}T00:00:00.0000000Z" if release_date else None,
        "DateCreated": f"{release_date}T00:00:00.0000000Z" if release_date else None,
        "RunTimeTicks": seconds_to_ticks(runtime_mins * 60) if runtime_mins else None,
        "CommunityRating": float(metadata.get("score") or 0) or None,
        "Overview": str(metadata.get("summary_translated") or metadata.get("summary") or ""),
        "ProviderIds": {"DvdId": str(metadata.get("dvd_id") or content_id)},
        "ImageTags": {"Primary": "jacket"},
        "BackdropImageTags": [],
        "UserData": _user_data(progress),
    }

    people = []
    for actress in metadata.get("actresses") or []:
        name = str(actress.get("name_kanji") or actress.get("name_romaji") or "").strip()
        if name:
            people.append({"Name": name, "Type": "Actor", "Role": ""})
    dto["People"] = people
    dto["Genres"] = [
        str(cat.get("name_ja_translated") or cat.get("name_ja") or cat.get("name_en") or "").strip()
        for cat in (metadata.get("categories") or [])
        if (cat.get("name_ja") or cat.get("name_en"))
    ]

    if detailed and files:
        dto["MediaSources"] = [media_source_dto(f, token=token) for f in files]
        dto["Container"] = _container_of(files[0].get("name"))

    return dto


def _user_data(progress: Optional[dict]) -> dict:
    if not progress:
        return {"PlaybackPositionTicks": 0, "PlayCount": 0, "Played": False, "IsFavorite": False}
    return {
        "PlaybackPositionTicks": seconds_to_ticks(progress.get("position_seconds")),
        "PlayCount": 1,
        "Played": bool(progress.get("completed")),
        "IsFavorite": False,
    }


def library_view_dto() -> dict:
    return {
        "Id": LIBRARY_VIEW_ID,
        "ServerId": SERVER_ID,
        "Name": "JavHub 影片库",
        "Type": "CollectionFolder",
        "CollectionType": "movies",
        "IsFolder": True,
        "ImageTags": {},
        "BackdropImageTags": [],
    }


def empty_result() -> dict:
    """未实现端点的统一回包：200 + 空集合（兼容层稳定性关键，绝不 404）。"""
    return {"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
