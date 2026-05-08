from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Query
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/supplement", tags=["supplement"])


@router.get("/stats")
async def supplement_stats() -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_get("/api/v1/supplement/stats", params=None)


@router.get("/actresses/{actress_id}/status")
async def supplement_actress_status(
    actress_id: int,
    source: str = Query("avbase"),
) -> dict[str, Any]:
    client = get_info_client()
    src = source.default if hasattr(source, "default") else source
    return await client.proxy_get(
        f"/api/v1/supplement/actresses/{actress_id}/status",
        params={"source": src},
    )


@router.post("/actresses/{actress_id}/filmography/jobs")
async def create_filmography_job(
    actress_id: int,
    source: str = Query("avbase"),
) -> dict[str, Any]:
    client = get_info_client()
    src = source.default if hasattr(source, "default") else source
    return await client.proxy_post(
        f"/api/v1/supplement/actresses/{actress_id}/filmography/jobs",
        params={"source": src},
    )


@router.post("/actresses/{actress_id}/resolved/refresh")
async def refresh_resolved(actress_id: int) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(
        f"/api/v1/supplement/actresses/{actress_id}/resolved/refresh",
        params=None,
    )


@router.get("/jobs")
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = Query(None),
    status: str | None = Query(None),
    actress_id: int | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    p = page.default if hasattr(page, "default") else page
    ps = page_size.default if hasattr(page_size, "default") else page_size
    src = source.default if hasattr(source, "default") else source
    st = status.default if hasattr(status, "default") else status
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    params: dict[str, Any] = {"page": p, "page_size": ps}
    if src:
        params["source"] = src
    if st:
        params["status"] = st
    if aid is not None:
        params["actress_id"] = aid
    return await client.proxy_get("/api/v1/supplement/jobs", params=params)


@router.get("/jobs/{job_id}")
async def get_job_detail(job_id: int) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_get(f"/api/v1/supplement/jobs/{job_id}")


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/jobs/{job_id}/retry")


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/jobs/{job_id}/cancel")


@router.post("/jobs/recover_stale")
async def recover_stale(
    older_than_minutes: int = Query(30, ge=1, le=1440),
) -> dict[str, Any]:
    client = get_info_client()
    otm = older_than_minutes.default if hasattr(older_than_minutes, "default") else older_than_minutes
    return await client.proxy_post(
        "/api/v1/supplement/jobs/recover_stale",
        params={"older_than_minutes": otm},
    )


@router.get("/movies")
async def list_supplement_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    matched: bool | None = Query(None),
    source: str | None = Query(None),
    actress_id: int | None = Query(None),
    q: str | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    p = page.default if hasattr(page, "default") else page
    ps = page_size.default if hasattr(page_size, "default") else page_size
    m = matched.default if hasattr(matched, "default") else matched
    src = source.default if hasattr(source, "default") else source
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    qv = q.default if hasattr(q, "default") else q
    params: dict[str, Any] = {"page": p, "page_size": ps}
    if m is not None:
        params["matched"] = "true" if m else "false"
    if src:
        params["source"] = src
    if aid is not None:
        params["actress_id"] = aid
    if qv:
        params["q"] = qv
    return await client.proxy_get("/api/v1/supplement/movies", params=params)
