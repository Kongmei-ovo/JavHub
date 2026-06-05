"""Bridge JavInfo supplement-only movies into local download candidates."""
from __future__ import annotations

import asyncio

from database import (
    add_download_candidate_event,
    candidate_content_id,
    is_video_exempt,
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
    limit: int | None = None,
    matched: bool | None = False,
    missing_cover: bool | None = None,
    missing_runtime: bool | None = None,
    missing_maker: bool | None = None,
    missing_categories: bool | None = None,
    max_completeness: int | None = None,
    concurrency: int = 10,
) -> dict:
    """Import unmatched supplement movies as download candidates.

    JavInfoApi remains the source of supplement truth. JavHub only snapshots the
    current unmatched rows into its local candidate queue for manual download
    approval.

    ``limit`` is an optional upper bound on source rows checked per request.
    Requests are paged with a maximum page size of 100 so large supplement
    result sets are processed across all available pages without asking
    JavInfoApi for an unbounded single response.
    """
    if info_client is None:
        from modules.info_client import get_info_client
        info_client = get_info_client()
    if emby_client is None:
        from modules.emby_client import get_emby_client
        emby_client = get_emby_client()

    max_source_rows = max(0, limit) if limit is not None else None
    page_size = min(max_source_rows, 100) if max_source_rows is not None else 100
    base_params: dict = {
        "page_size": page_size,
    }
    if matched is not None:
        base_params["matched"] = "true" if matched else "false"
    if actress_id is not None:
        base_params["actress_id"] = actress_id
    if supplement_source:
        base_params["source"] = supplement_source
    if q:
        base_params["q"] = q
    if missing_cover is not None:
        base_params["missing_cover"] = "true" if missing_cover else "false"
    if missing_runtime is not None:
        base_params["missing_runtime"] = "true" if missing_runtime else "false"
    if missing_maker is not None:
        base_params["missing_maker"] = "true" if missing_maker else "false"
    if missing_categories is not None:
        base_params["missing_categories"] = "true" if missing_categories else "false"
    if max_completeness is not None:
        base_params["max_completeness"] = max_completeness

    stats = {
        "checked": 0,
        "created": 0,
        "existing": 0,
        "skipped": 0,
        "skipped_exempt": 0,
        "in_library": 0,
        "errors": 0,
        "candidate_count": 0,
        "candidates": [],
    }

    sem = asyncio.Semaphore(max(1, concurrency))

    async def evaluate_movie(movie: dict) -> dict:
        """Decide what to do with a movie. Does the slow Emby existence check
        under a concurrency bound; performs no DB writes and never raises."""
        if movie.get("status") == "manual_ignored" or movie.get("match_status") == "manual_ignored":
            return {"action": "skipped", "movie": movie}

        video = supplement_movie_to_video(movie)
        content_id = candidate_content_id(video)
        code = video_code(video)
        if not content_id or not code:
            return {"action": "skipped", "movie": movie}

        if is_video_exempt(content_id) or is_video_exempt(code):
            return {"action": "exempt", "movie": movie}

        async with sem:
            try:
                exists = await emby_client.check_exists(code)
            except Exception as exc:  # one Emby hiccup must not abort the whole batch
                return {"action": "error", "movie": movie, "error": str(exc)}
        if exists:
            return {"action": "in_library", "movie": movie}
        return {"action": "candidate", "movie": movie, "video": video}

    def apply_decision(decision: dict) -> None:
        action = decision["action"]
        movie = decision["movie"]
        if action == "skipped":
            stats["skipped"] += 1
            return
        # Everything below passed code validation, so it counts as "checked".
        stats["checked"] += 1
        if action == "exempt":
            stats["skipped"] += 1
            stats["skipped_exempt"] += 1
            return
        if action == "error":
            stats["errors"] += 1
            return
        if action == "in_library":
            stats["in_library"] += 1
            return

        candidate = upsert_candidate_from_video(
            video=decision["video"],
            actress_id=movie.get("local_actress_id") or actress_id,
            actress_name=movie.get("actress_name") or actress_name,
            source="supplement",
            reason="supplement_only",
            return_insert_status=True,
        )
        was_inserted = bool(candidate.pop("was_inserted", False))
        if was_inserted:
            add_download_candidate_event(
                candidate["id"],
                "supplement_imported",
                f"supplement_movie_id={movie.get('id')}",
                "system",
            )
        stats["candidates"].append(candidate)
        stats["candidate_count"] += 1
        if was_inserted:
            stats["created"] += 1
        else:
            stats["existing"] += 1

    page = 1
    source_rows_seen = 0
    while page_size and (max_source_rows is None or source_rows_seen < max_source_rows):
        params = {**base_params, "page": page}
        result = await info_client.proxy_get("/api/v1/supplement/movies", params=params)
        movies = result.get("data", []) if isinstance(result, dict) else []
        if not movies:
            break

        batch = []
        for movie in movies:
            if max_source_rows is not None and source_rows_seen >= max_source_rows:
                break
            source_rows_seen += 1
            batch.append(movie)

        # Phase 1: existence checks fan out (bounded); Phase 2: DB writes stay ordered.
        decisions = await asyncio.gather(*(evaluate_movie(movie) for movie in batch))
        for decision in decisions:
            apply_decision(decision)

        total_pages = result.get("total_pages") if isinstance(result, dict) else None
        if isinstance(total_pages, int):
            if page >= total_pages:
                break
        elif len(movies) < page_size:
            break
        page += 1

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
