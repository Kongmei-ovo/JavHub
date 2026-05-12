"""Bridge JavInfo supplement-only movies into local download candidates."""
from __future__ import annotations

from database import (
    add_download_candidate_event,
    candidate_content_id,
    is_video_exempt,
    list_download_candidates,
    upsert_candidate_from_video,
)
from services.watchlist_pipeline import video_code


def supplement_movie_to_video(movie: dict) -> dict:
    content_id = (
        movie.get("matched_content_id")
        or movie.get("canonical_number")
        or movie.get("dvd_id")
        or movie.get("source_movie_id")
        or movie.get("id")
    )
    dvd_id = movie.get("dvd_id") or movie.get("canonical_number") or content_id
    return {
        "content_id": content_id,
        "dvd_id": dvd_id,
        "canonical_number": movie.get("canonical_number"),
        "title": movie.get("title"),
        "title_ja": movie.get("title"),
        "release_date": movie.get("release_date"),
    }


async def generate_download_candidates_from_supplement(
    info_client=None,
    emby_client=None,
    actress_id: int | None = None,
    actress_name: str = "",
    supplement_source: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> dict:
    """Import unmatched supplement movies as download candidates.

    JavInfoApi remains the source of supplement truth. JavHub only snapshots the
    current unmatched rows into its local candidate queue for manual download
    approval.
    """
    if info_client is None:
        from modules.info_client import get_info_client
        info_client = get_info_client()
    if emby_client is None:
        from modules.emby_client import get_emby_client
        emby_client = get_emby_client()

    params: dict = {
        "page": 1,
        "page_size": limit,
        "matched": "false",
    }
    if actress_id is not None:
        params["actress_id"] = actress_id
    if supplement_source:
        params["source"] = supplement_source
    if q:
        params["q"] = q

    result = await info_client.proxy_get("/api/v1/supplement/movies", params=params)
    movies = result.get("data", []) if isinstance(result, dict) else []
    existing_candidates = {
        (row.get("content_id"), row.get("source"))
        for row in list_download_candidates(
            source="supplement",
            limit=100000,
        )
    }

    stats = {
        "checked": 0,
        "created": 0,
        "existing": 0,
        "skipped": 0,
        "skipped_exempt": 0,
        "in_library": 0,
        "candidate_count": 0,
        "candidates": [],
    }

    for movie in movies:
        if movie.get("status") == "manual_ignored" or movie.get("match_status") == "manual_ignored":
            stats["skipped"] += 1
            continue

        video = supplement_movie_to_video(movie)
        content_id = candidate_content_id(video)
        code = video_code(video)
        if not content_id or not code:
            stats["skipped"] += 1
            continue

        stats["checked"] += 1
        if is_video_exempt(content_id) or is_video_exempt(code):
            stats["skipped"] += 1
            stats["skipped_exempt"] += 1
            continue

        if await emby_client.check_exists(code):
            stats["in_library"] += 1
            continue

        existed = (content_id, "supplement") in existing_candidates
        candidate = upsert_candidate_from_video(
            video=video,
            actress_id=movie.get("local_actress_id") or actress_id,
            actress_name=movie.get("actress_name") or actress_name,
            source="supplement",
            reason="supplement_only",
        )
        if not existed:
            add_download_candidate_event(
                candidate["id"],
                "supplement_imported",
                f"supplement_movie_id={movie.get('id')}",
                "system",
            )
        stats["candidates"].append(candidate)
        stats["candidate_count"] += 1
        if existed:
            stats["existing"] += 1
        else:
            stats["created"] += 1
            existing_candidates.add((content_id, "supplement"))

    stats["new_movies_count"] = stats["candidate_count"]
    stats["new_movies"] = [
        {
            "candidate_id": c.get("id"),
            "content_id": c.get("content_id"),
            "dvd_id": c.get("dvd_id"),
            "code": c.get("dvd_id") or c.get("content_id"),
            "title": c.get("title"),
            "release_date": c.get("release_date"),
            "actress_name": c.get("actress_name"),
        }
        for c in stats["candidates"]
    ]
    return stats
