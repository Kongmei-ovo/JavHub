"""JavInfo metadata plus ItemId-bound resources to Emby DTOs.

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


def media_source_dto(resource: dict, item_id: str, token: str = "") -> dict:
    """A real 115 file becomes one selectable Emby media source."""
    source_id = f"open115:{resource['id']}"
    container = str(resource.get("extension") or _container_of(resource.get("name"))).lower().lstrip(".")
    stream_url = f"/Videos/{item_id}/stream.{container}?MediaSourceId={source_id}&Static=true"
    if token:
        stream_url += f"&api_key={token}"
    source = {
        "Id": source_id,
        "Protocol": "Http",
        "Container": container,
        "Size": int(resource.get("size") or 0),
        "Name": resource.get("name") or "",
        "Path": stream_url,
        "IsRemote": True,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": container not in {"mp4", "webm"},
        "Type": "Default",
        "RunTimeTicks": seconds_to_ticks(resource.get("duration")),
        "RequiresOpening": False,
        "RequiresClosing": False,
        "SupportsProbing": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [
            {
                "Codec": "unknown",
                "Type": "Video",
                "Index": 0,
                "IsDefault": True,
                "IsForced": False,
                "IsExternal": False,
                "DisplayTitle": container.upper() or "Video",
            }
        ],
        "RequiredHttpHeaders": {},
    }
    if source["SupportsTranscoding"]:
        hls_url = f"/Videos/{item_id}/stream.m3u8?MediaSourceId={source_id}&mode=hls&Static=true"
        if token:
            hls_url += f"&api_key={token}"
        source["TranscodingUrl"] = hls_url
        source["TranscodingContainer"] = "m3u8"
        source["TranscodingSubProtocol"] = "hls"
    return source


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
        "Path": stream_url,
        "IsRemote": True,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": False,
        "Type": "Default",
        "RequiresOpening": False,
        "RequiresClosing": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [
            {
                "Codec": "h264",
                "Type": "Video",
                "Index": 0,
                "IsDefault": True,
                "IsForced": False,
                "IsExternal": False,
                "DisplayTitle": "Online HLS",
            }
        ],
        "RequiredHttpHeaders": {},
    }


def to_base_item_dto(
    content_id: str,
    metadata: Optional[dict],
    resources: Optional[list[dict]] = None,
    progress: Optional[dict] = None,
    is_favorite: bool = False,
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
        "ProviderIds": {
            "JavHub": content_id,
            "DvdId": str(metadata.get("dvd_id") or content_id),
        },
        "ImageTags": (
            {"Primary": "jacket"}
            if metadata.get("jacket_full_url") or metadata.get("jacket_thumb_url")
            else {}
        ),
        "BackdropImageTags": (
            ["backdrop"]
            if metadata.get("backdrop_url") or metadata.get("sample_image_urls")
            else []
        ),
        "UserData": _user_data(progress, is_favorite=is_favorite),
        "CanDelete": False,
        "CanDownload": False,
        "PlayAccess": "Full",
        "ExternalUrls": [],
        "Tags": [
            str(tag.get("name") if isinstance(tag, dict) else tag)
            for tag in (metadata.get("tags") or [])
            if str(tag.get("name") if isinstance(tag, dict) else tag).strip()
        ],
    }

    people = []
    for actress in metadata.get("actresses") or []:
        name = str(actress.get("name_kanji") or actress.get("name_romaji") or "").strip()
        if name:
            actress_id = str(actress.get("id") or "").strip()
            person = {"Name": name, "Type": "Actor", "Role": ""}
            if actress_id:
                person["Id"] = f"person:{actress_id}"
            if actress.get("image_url") or actress.get("avatar_url"):
                person["PrimaryImageTag"] = "avatar"
            people.append(person)
    dto["People"] = people
    genres = []
    genre_items = []
    for category in metadata.get("categories") or []:
        name = str(
            category.get("name_ja_translated")
            or category.get("name_ja")
            or category.get("name_en")
            or ""
        ).strip()
        if not name:
            continue
        genres.append(name)
        genre_items.append({"Name": name, "Id": f"genre:{category.get('id') or name}"})
    dto["Genres"] = genres
    dto["GenreItems"] = genre_items

    studios = []
    for field in ("maker", "label"):
        entity = metadata.get(field)
        if isinstance(entity, dict):
            name = str(
                entity.get("name_translated")
                or entity.get("name_ja")
                or entity.get("name_en")
                or entity.get("name")
                or ""
            ).strip()
            if name:
                studios.append({"Name": name, "Id": f"{field}:{entity.get('id') or name}"})
    dto["Studios"] = studios
    series = metadata.get("series")
    if isinstance(series, dict):
        series_name = str(
            series.get("name_translated")
            or series.get("name_ja")
            or series.get("name_en")
            or series.get("name")
            or ""
        ).strip()
        if series_name:
            dto["SeriesName"] = series_name
            dto["SeriesId"] = f"series:{series.get('id') or series_name}"

    ready_videos = [
        resource for resource in (resources or [])
        if resource.get("resource_type") == "video" and resource.get("status") == "ready"
    ]
    ready_videos.sort(
        key=lambda resource: (
            not bool(resource.get("is_default")),
            -int(resource.get("size") or 0),
        )
    )
    if detailed and ready_videos:
        dto["MediaSources"] = [
            media_source_dto(resource, content_id, token=token)
            for resource in ready_videos
        ]
        dto["Container"] = str(
            ready_videos[0].get("extension") or _container_of(ready_videos[0].get("name"))
        ).lower().lstrip(".")

    return dto


def _user_data(progress: Optional[dict], *, is_favorite: bool = False) -> dict:
    if not progress:
        return {
            "PlaybackPositionTicks": 0,
            "PlayCount": 0,
            "Played": False,
            "IsFavorite": is_favorite,
            "IsResumable": False,
            "PlayedPercentage": 0,
            "PercentagePlayed": 0,
            "UnplayedItemCount": 1,
        }
    position = float(progress.get("position_seconds") or 0)
    duration = float(progress.get("duration_seconds") or 0)
    percentage = min(position / duration * 100, 100) if duration > 0 else 0
    played = bool(progress.get("completed"))
    updated_at = progress.get("updated_at")
    if updated_at is not None and not isinstance(updated_at, str):
        updated_at = updated_at.isoformat()
    result = {
        "PlaybackPositionTicks": seconds_to_ticks(position),
        "PlayCount": 1 if played else 0,
        "Played": played,
        "IsFavorite": is_favorite,
        "IsResumable": bool(position > 0 and not played),
        "PlayedPercentage": percentage,
        "PercentagePlayed": percentage,
        "UnplayedItemCount": 0 if played else 1,
    }
    if updated_at:
        result["LastPlayedDate"] = str(updated_at)
    return result


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
