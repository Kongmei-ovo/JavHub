"""JavInfo metadata plus ItemId-bound resources to Emby DTOs.

字段依据 Jellyfin OpenAPI（https://api.jellyfin.org）/ Emby 公开协议；
不参考任何 GPL 实现。只输出 Infuse/VidHub 实际消费的最小字段集。

时长/进度单位为 Ticks：1 tick = 100ns，秒 × 10_000_000。
"""
from __future__ import annotations

from typing import Optional

from services.emby_images import (
    actress_image_url,
    image_tag,
    movie_backdrop_image_urls,
    movie_primary_image_url,
)

TICKS_PER_SECOND = 10_000_000
SERVER_ID = "javhub-emby-compat"
LIBRARY_VIEW_ID = "library"


def seconds_to_ticks(seconds: float | int | None) -> int:
    return int(float(seconds or 0) * TICKS_PER_SECOND)


def ticks_to_seconds(ticks: float | int | None) -> float:
    return float(ticks or 0) / TICKS_PER_SECOND


def _community_rating(score: object) -> float | None:
    try:
        value = float(score or 0)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    # JavInfo providers expose five-star review scores. Emby displays a
    # ten-point CommunityRating.
    return min(value * 2, 10.0)


def _person_name(item: dict) -> str:
    return str(
        item.get("name_kanji_translated")
        or item.get("name_kanji")
        or item.get("name_romaji_translated")
        or item.get("name_romaji")
        or item.get("name_kana")
        or item.get("name")
        or ""
    ).strip()


def to_base_item_dto(
    content_id: str,
    metadata: Optional[dict],
    progress: Optional[dict] = None,
    is_favorite: bool = False,
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
    primary_image = movie_primary_image_url(metadata)
    backdrop_images = movie_backdrop_image_urls(metadata)

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
        "CommunityRating": _community_rating(metadata.get("score")),
        "Overview": str(metadata.get("summary_translated") or metadata.get("summary") or ""),
        "ProviderIds": {
            "JavHub": content_id,
            "DvdId": str(metadata.get("dvd_id") or content_id),
        },
        "ImageTags": {"Primary": image_tag(primary_image)} if primary_image else {},
        "BackdropImageTags": [image_tag(url) for url in backdrop_images],
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
        name = _person_name(actress)
        if name:
            actress_id = str(actress.get("id") or "").strip()
            person = {"Name": name, "Type": "Actor", "Role": ""}
            if actress_id:
                person["Id"] = f"person:{actress_id}"
            avatar = actress_image_url(actress)
            if avatar:
                person["PrimaryImageTag"] = image_tag(avatar)
            people.append(person)
    for field, person_type in (
        ("actors", "Actor"),
        ("directors", "Director"),
        ("authors", "Writer"),
    ):
        for item in metadata.get(field) or []:
            name = _person_name(item)
            if name:
                people.append({"Name": name, "Type": person_type, "Role": ""})
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
