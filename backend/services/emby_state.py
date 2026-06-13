"""Bridge Emby user-state writes to JavHub's existing state stores."""
from __future__ import annotations

from database import (
    delete_progress,
    get_progress,
    get_variant_group_by_content_ids,
    list_playback_progress,
    save_progress,
)
from database import favorite as favorite_db
from database.playback import MIN_RESUME_SECONDS


def _favorite_members(movie_id: str) -> list[tuple[str, dict]]:
    members: list[tuple[str, dict]] = [(movie_id, {"content_id": movie_id})]
    try:
        indexed = get_variant_group_by_content_ids([movie_id])
    except Exception:
        indexed = {}
    group = indexed.get(movie_id) if isinstance(indexed, dict) else None
    if not group:
        return members

    members = []
    for item in group.get("items") or []:
        content_id = str(item.get("content_id") or "").strip()
        if not content_id:
            continue
        service_code = str(item.get("service_code") or "").strip()
        entity_id = f"{content_id}::{service_code}" if service_code else content_id
        members.append(
            (
                entity_id,
                {
                    "content_id": content_id,
                    "dvd_id": item.get("dvd_id") or "",
                    "service_code": service_code,
                    "variant_group_id": group.get("group_id"),
                    "canonical_code": group.get("canonical_code"),
                    "variant_group_size": group.get("group_count"),
                },
            )
        )
    if movie_id not in {member_id for member_id, _ in members}:
        members.append((movie_id, {"content_id": movie_id}))
    return members


def set_movie_favorite(movie_id: str, favorited: bool) -> None:
    for entity_id, metadata in _favorite_members(movie_id):
        favorite_db.set_favorite("video", entity_id, metadata, favorited=favorited)


def is_movie_favorite(movie_id: str) -> bool:
    return any(
        favorite_db.is_favorite("video", entity_id)
        for entity_id, _metadata in _favorite_members(movie_id)
    )


def movie_favorite_flags(movie_ids: list[str]) -> dict[str, bool]:
    """Resolve favorite state for a page with one favorite and one group query."""
    ids = list(dict.fromkeys(str(movie_id) for movie_id in movie_ids if movie_id))
    if not ids:
        return {}
    favorite_ids = {
        str(row.get("entity_id") or "")
        for row in favorite_db.list_favorite_index("video")
    }
    try:
        indexed = get_variant_group_by_content_ids(ids)
    except Exception:
        indexed = {}
    result: dict[str, bool] = {}
    for movie_id in ids:
        candidates = {movie_id}
        group = indexed.get(movie_id) if isinstance(indexed, dict) else None
        for item in (group or {}).get("items") or []:
            content_id = str(item.get("content_id") or "").strip()
            service_code = str(item.get("service_code") or "").strip()
            if content_id:
                candidates.add(f"{content_id}::{service_code}" if service_code else content_id)
        result[movie_id] = bool(candidates.intersection(favorite_ids))
    return result


def _favorite_movie_ids() -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for row in favorite_db.list_favorite_index("video"):
        movie_id = str(row.get("entity_id") or "").split("::", 1)[0].strip()
        if movie_id and movie_id not in seen:
            seen.add(movie_id)
            result.append(movie_id)
    return result


def _canonical_movie_ids(movie_ids: list[str]) -> list[str]:
    ids = list(dict.fromkeys(movie_ids))
    try:
        indexed = get_variant_group_by_content_ids(ids)
    except Exception:
        indexed = {}
    result: list[str] = []
    seen: set[str] = set()
    for movie_id in ids:
        group = indexed.get(movie_id) if isinstance(indexed, dict) else None
        canonical = str((group or {}).get("primary_content_id") or movie_id)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def select_state_movie_ids(filters: str, sort_by: str, sort_order: str) -> list[str] | None:
    """Return a state-backed movie index, or None for ordinary catalog browsing."""
    filter_set = {
        part.strip().casefold()
        for part in str(filters or "").split(",")
        if part.strip()
    }
    sort_fields = {
        part.strip().casefold()
        for part in str(sort_by or "").split(",")
        if part.strip()
    }
    needs_favorites = "isfavorite" in filter_set
    needs_resume = "isresumable" in filter_set
    needs_played = "isplayed" in filter_set
    date_played_sort = "dateplayed" in sort_fields
    if not (needs_favorites or needs_resume or needs_played or date_played_sort):
        return None

    progress_rows = list_playback_progress(source="library")
    progress_ids = []
    for row in progress_rows:
        if needs_resume and (
            bool(row.get("completed"))
            or float(row.get("position_seconds") or 0) < MIN_RESUME_SECONDS
        ):
            continue
        if needs_played and not bool(row.get("completed")):
            continue
        content_id = str(row.get("content_id") or "").strip()
        if content_id:
            progress_ids.append(content_id)

    favorite_ids = _favorite_movie_ids() if needs_favorites else []
    if needs_favorites and (needs_resume or needs_played or date_played_sort):
        favorite_set = set(favorite_ids)
        selected = [movie_id for movie_id in progress_ids if movie_id in favorite_set]
    elif needs_favorites:
        selected = favorite_ids
    else:
        selected = progress_ids

    descending = not str(sort_order or "").casefold().startswith("asc")
    if not descending:
        selected.reverse()
    return _canonical_movie_ids(selected)


def mark_movie_played(movie_id: str, played: bool) -> None:
    if not played:
        delete_progress(movie_id, source="library")
        return
    existing = get_progress(movie_id, source="library") or {}
    duration = max(float(existing.get("duration_seconds") or 0), 1.0)
    save_progress(movie_id, "library", duration, duration)
