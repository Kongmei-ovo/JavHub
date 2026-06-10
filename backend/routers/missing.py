from fastapi import APIRouter, HTTPException, Query
from typing import Any
import asyncio
from database import (
    get_inventory_actor,
    get_missing_videos,
    list_missing_actresses_from_inventory,
)
from services import cache as response_cache
from services.cache import should_bypass_response_cache

router = APIRouter(prefix="/api/v1/missing", tags=["missing"])


@router.get("/actresses")
async def list_missing_actresses(cache_control: str | None = Query(None, alias="cache")) -> dict[str, Any]:
    """List actresses with missing works.

    Reads directly from ``inventory.missing_videos`` (the same table the
    inventory compare writes to) — the legacy "subscription + per-actress
    Emby check" path is intentionally bypassed because it double-counted,
    capped at the first 100 works per actress, and broke under Emby flaps.
    """
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {"generation": await response_cache.get_data_generation_async("missing_summaries")}

    async def produce() -> dict[str, Any]:
        summaries = await asyncio.to_thread(list_missing_actresses_from_inventory)
        return {
            "data": summaries,
            "total": len(summaries),
        }

    return await response_cache.get_or_set_response(
        "missing_actresses",
        cache_params,
        produce,
        ttl=5,
        bypass=bypass_cache,
    )


@router.get("/actresses/{actress_id}")
def get_missing_actress_detail(actress_id: int) -> dict[str, Any]:
    """Return missing works for one actress, grouped by year (newest first)."""
    actor = get_inventory_actor(actress_id)
    rows = get_missing_videos(actress_id)
    if not rows and not actor:
        raise HTTPException(status_code=404, detail="Actor not found in missing inventory")

    videos_by_year: dict[str, list] = {}
    for row in rows:
        release_date = row.get("release_date") or ""
        year = release_date[:4] if release_date else "未知"
        videos_by_year.setdefault(year, []).append({
            "content_id": row.get("content_id"),
            "title": row.get("title"),
            "release_date": release_date,
            "jacket_thumb_url": row.get("jacket_thumb_url"),
        })

    for year in videos_by_year:
        videos_by_year[year].sort(
            key=lambda x: x.get("release_date") or "",
            reverse=True,
        )

    return {
        "actress_id": actress_id,
        "actress_name": (actor or {}).get("primary_name") or (actor or {}).get("actress_name") or "",
        "missing_count": len(rows),
        "videos_by_year": videos_by_year,
    }


@router.post("/actresses/refresh")
async def refresh_missing_cache() -> dict[str, Any]:
    """Kick a fresh inventory compare so missing_videos is rebuilt.

    The route is kept for backward compatibility with the existing UI button
    that used to call the legacy slow path. It now triggers a real
    end-to-end pipeline so the numbers stay consistent with the rest of
    the inventory module.
    """
    from database import add_inventory_job
    from scheduler.inventory_tasks import run_inventory_job

    job_id = add_inventory_job("full")
    run_inventory_job(job_id, mode="full")
    return {"status": "ok", "job_id": job_id}
