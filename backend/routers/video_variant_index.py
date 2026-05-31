from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from database.video_variant_index import (
    get_variant_group_job,
    list_variant_group_jobs,
    variant_group_stats,
)
from services.cache import get_or_set_response, should_bypass_response_cache
from services.video_variant_index import start_variant_index_job

router = APIRouter(prefix="/api/v1/video-variants/index", tags=["video-variant-index"])


@router.post("/jobs")
def create_variant_index_job() -> dict[str, Any]:
    return start_variant_index_job()


@router.get("/jobs")
def list_variant_index_jobs(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    return {"data": list_variant_group_jobs(limit=limit)}


@router.get("/jobs/{job_id}")
def get_variant_index_job(job_id: int) -> dict[str, Any]:
    job = get_variant_group_job(job_id)
    if not job:
        raise HTTPException(404, "variant index job not found")
    return job


@router.get("/stats")
async def get_variant_index_stats(cache_control: str | None = Query(None, alias="cache")) -> dict[str, Any]:
    async def produce() -> dict[str, Any]:
        return await asyncio.to_thread(variant_group_stats)

    return await get_or_set_response(
        "video_variant_index_stats",
        {},
        produce,
        ttl=5,
        bypass=should_bypass_response_cache(cache_control),
    )
