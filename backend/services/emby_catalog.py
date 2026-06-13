"""Catalog helpers shared by Emby route variants."""
from __future__ import annotations

from typing import Any

from services.video_variant_index import apply_indexed_variant_groups
from services.video_variants import enrich_video_variants, filter_movie_items

PERSON_PREFIX = "person:"


def split_csv(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def parse_person_id(value: str) -> int | None:
    text = str(value or "").strip()
    if text.lower().startswith(PERSON_PREFIX):
        text = text[len(PERSON_PREFIX):]
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def actress_name(item: dict) -> str:
    return str(
        item.get("name_kanji_translated")
        or item.get("name_kanji")
        or item.get("name_romaji_translated")
        or item.get("name_romaji")
        or item.get("name")
        or f"演员 {item.get('id', '')}"
    ).strip()


def actress_image_url(item: dict) -> str:
    return str(
        item.get("image_url")
        or item.get("avatar_url")
        or item.get("javinfo_avatar_url")
        or ""
    ).strip()


def person_dto(item: dict, *, detailed: bool = False) -> dict:
    actress_id = str(item.get("id") or "").strip()
    dto = {
        "Id": f"{PERSON_PREFIX}{actress_id}",
        "Name": actress_name(item),
        "Type": "Person",
        "IsFolder": False,
        "MediaType": "Unknown",
        "ImageTags": {"Primary": "avatar"} if actress_image_url(item) else {},
        "ProviderIds": {"JavInfoActress": actress_id},
        "RecursiveItemCount": int(item.get("movie_count") or item.get("video_count") or 0),
        "ChildCount": 0,
    }
    if detailed:
        dto.update(
            {
                "Overview": str(item.get("description") or item.get("overview") or ""),
                "SortName": actress_name(item),
                "PremiereDate": item.get("birth_date") or None,
            }
        )
    return dto


def group_movie_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply JavHub's movie-only and variant grouping policy."""
    movie_items = filter_movie_items([dict(item) for item in items])
    grouped = enrich_video_variants(movie_items, variant_mode="grouped")
    indexed = apply_indexed_variant_groups(grouped)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in indexed:
        variants = item.get("variant_group_items") if isinstance(item.get("variant_group_items"), list) else []
        primary_id = str((variants[0] if variants else {}).get("content_id") or item.get("content_id") or "")
        identity = primary_id or str(item.get("content_id") or item.get("dvd_id") or "")
        if identity in seen:
            continue
        seen.add(identity)
        row = dict(item)
        if primary_id:
            row["content_id"] = primary_id
        result.append(row)
    return result


def sort_grouped_movies(items: list[dict], sort_by: str, sort_order: str) -> list[dict]:
    descending = str(sort_order or "").lower().startswith("desc")
    field = split_csv(sort_by)[0].lower() if split_csv(sort_by) else "datecreated"

    def key(item: dict):
        if field in {"sortname", "name"}:
            return str(item.get("title_ja_translated") or item.get("title_ja") or item.get("title_en") or "").casefold()
        if field in {"communityrating", "criticrating"}:
            return float(item.get("score") or 0)
        if field == "runtime":
            return int(item.get("runtime_mins") or 0)
        return str(item.get("release_date") or "")

    return sorted(items, key=key, reverse=descending)
