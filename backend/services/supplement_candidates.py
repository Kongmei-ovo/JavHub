"""Bridge JavInfo supplement-only movies into local download candidates."""
from __future__ import annotations

from database import (
    add_download_candidate_event,
    candidate_content_id,
    codes_with_ready_resource,
    is_video_exempt,
    upsert_candidate_from_video,
)
from modules.code_matcher import video_code


def generate_download_candidates_from_catalog(
    films: list[dict],
    *,
    actress_id: int,
    actress_name: str = "",
    canonical_number: str = "",
    limit: int | None = None,
) -> dict:
    """Bridge the canonical actress dictionary into the candidate queue.

    The catalog's acquisition stage contains native *and* supplement-only
    films.  Using ``supplement_movies`` as the source here silently drops every
    canonical-only native work, so this bridge consumes the same completeness
    snapshot that produced the UI count.
    """
    wanted = "".join(ch for ch in str(canonical_number or "").upper() if ch.isalnum())
    selected: list[dict] = []
    for film in films or []:
        if film.get("funnel_stage") != "find_source":
            continue
        normalized = "".join(
            ch for ch in str(film.get("canonical_number") or "").upper() if ch.isalnum()
        )
        if wanted and normalized != wanted:
            continue
        selected.append(film)
        if limit and len(selected) >= limit:
            break

    stats = {
        "checked": len(selected),
        "created": 0,
        "existing": 0,
        "skipped": 0,
        "candidate_ids": [],
    }
    for film in selected:
        existing_ids = [int(value) for value in film.get("candidate_ids") or [] if value]
        if existing_ids:
            stats["existing"] += 1
            stats["candidate_ids"].extend(existing_ids)
            continue

        canonical = str(film.get("canonical_number") or "").strip()
        if not canonical or is_video_exempt(canonical):
            stats["skipped"] += 1
            continue
        candidate = upsert_candidate_from_video(
            video={
                "content_id": canonical,
                "dvd_id": film.get("display_code") or canonical,
                "title": film.get("title") or canonical,
                "release_date": film.get("release_date"),
                "jacket_thumb_url": film.get("cover_url"),
            },
            actress_id=actress_id,
            actress_name=actress_name,
            source="supplement",
            reason="catalog_acquisition_gap",
            return_insert_status=True,
        )
        inserted = bool(candidate.pop("was_inserted", False))
        stats["created" if inserted else "existing"] += 1
        if candidate.get("id"):
            stats["candidate_ids"].append(int(candidate["id"]))
        if inserted:
            add_download_candidate_event(
                candidate["id"],
                "catalog_imported",
                f"canonical_number={canonical}",
                "system",
            )
    return stats


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

    def evaluate_movie(movie: dict, ready_codes: set[str]) -> dict:
        """Decide what to do with a movie against local ownership; performs no DB
        writes and never raises."""
        if movie.get("status") == "manual_ignored" or movie.get("match_status") == "manual_ignored":
            return {"action": "skipped", "movie": movie}

        video = supplement_movie_to_video(movie)
        content_id = candidate_content_id(video)
        code = video_code(video)
        if not content_id or not code:
            return {"action": "skipped", "movie": movie}

        if is_video_exempt(content_id) or is_video_exempt(code):
            return {"action": "exempt", "movie": movie}

        # Skip what we already own. Replaces the removed Emby library probe with
        # the local 115 / movie_resources ledger (keyed by canonical 番号 or content_id).
        if content_id in ready_codes or code in ready_codes:
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

        # Resolve local ownership for the whole page in one ledger lookup, then
        # decide each movie (no remote calls; DB writes stay ordered).
        ownership_lookup: list[str] = []
        for movie in batch:
            owned_probe = supplement_movie_to_video(movie)
            ownership_lookup.append(candidate_content_id(owned_probe))
            ownership_lookup.append(video_code(owned_probe))
        ready_codes = codes_with_ready_resource([code for code in ownership_lookup if code])
        for movie in batch:
            apply_decision(evaluate_movie(movie, ready_codes))

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
