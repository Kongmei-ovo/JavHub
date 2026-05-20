from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Query
from modules.info_client import get_info_client
from services.supplement_candidates import generate_download_candidates_from_supplement
from translations import get_translator_service

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
    missing_cover: bool | None = Query(None),
    missing_runtime: bool | None = Query(None),
    missing_maker: bool | None = Query(None),
    missing_categories: bool | None = Query(None),
    max_completeness: int | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    p = page.default if hasattr(page, "default") else page
    ps = page_size.default if hasattr(page_size, "default") else page_size
    m = matched.default if hasattr(matched, "default") else matched
    src = source.default if hasattr(source, "default") else source
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    qv = q.default if hasattr(q, "default") else q
    mc = missing_cover.default if hasattr(missing_cover, "default") else missing_cover
    mr = missing_runtime.default if hasattr(missing_runtime, "default") else missing_runtime
    mm = missing_maker.default if hasattr(missing_maker, "default") else missing_maker
    mcat = missing_categories.default if hasattr(missing_categories, "default") else missing_categories
    maxc = max_completeness.default if hasattr(max_completeness, "default") else max_completeness
    params: dict[str, Any] = {"page": p, "page_size": ps}
    if m is not None:
        params["matched"] = "true" if m else "false"
    if src:
        params["source"] = src
    if aid is not None:
        params["actress_id"] = aid
    if qv:
        params["q"] = qv
    if mc is not None:
        params["missing_cover"] = "true" if mc else "false"
    if mr is not None:
        params["missing_runtime"] = "true" if mr else "false"
    if mm is not None:
        params["missing_maker"] = "true" if mm else "false"
    if mcat is not None:
        params["missing_categories"] = "true" if mcat else "false"
    if maxc is not None:
        params["max_completeness"] = maxc
    return await client.proxy_get("/api/v1/supplement/movies", params=params)


@router.get("/movies/{movie_id}/sources")
async def get_movie_sources(movie_id: int) -> dict[str, Any]:
    client = get_info_client()
    data = await client.proxy_get(f"/api/v1/supplement/movies/{movie_id}/sources")
    return await get_translator_service().translate_supplement_sources(data, allow_network=False)


@router.post("/movies/candidates")
async def create_download_candidates_from_supplement(
    actress_id: int | None = Query(None),
    actress_name: str = Query(""),
    source: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    name = actress_name.default if hasattr(actress_name, "default") else actress_name
    src = source.default if hasattr(source, "default") else source
    qv = q.default if hasattr(q, "default") else q
    lim = limit.default if hasattr(limit, "default") else limit
    result = await generate_download_candidates_from_supplement(
        actress_id=aid,
        actress_name=name,
        supplement_source=src,
        q=qv,
        limit=lim,
    )
    return {"status": "ok", **result}


@router.post("/movies/{movie_id}/match")
async def match_movie(movie_id: int, body: dict[str, Any]) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/movies/{movie_id}/match", json_body=body)


@router.post("/movies/{movie_id}/ignore")
async def ignore_movie(movie_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/movies/{movie_id}/ignore", json_body=body or {})


@router.post("/movies/{movie_id}/unmatch")
async def unmatch_movie(movie_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/movies/{movie_id}/unmatch", json_body=body or {})


@router.get("/sources")
async def list_sources() -> list[dict[str, Any]]:
    client = get_info_client()
    return await client.proxy_get("/api/v1/supplement/sources", params=None)


@router.get("/sources/health")
async def list_sources_health() -> list[dict[str, Any]]:
    client = get_info_client()
    return await client.proxy_get("/api/v1/supplement/sources/health", params=None)


@router.get("/sources/budgets")
async def list_sources_budgets() -> list[dict[str, Any]]:
    client = get_info_client()
    return await client.proxy_get("/api/v1/supplement/sources/budgets", params=None)


@router.post("/providers/smoke")
async def run_provider_smoke(body: dict[str, Any] | None = None) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post("/api/v1/supplement/providers/smoke", json_body=body or {})


@router.get("/providers/smoke/runs")
async def list_provider_smoke_runs(
    limit: int = Query(10, ge=1, le=50),
    source: str | None = Query(None),
) -> list[dict[str, Any]]:
    client = get_info_client()
    lim = limit.default if hasattr(limit, "default") else limit
    src = source.default if hasattr(source, "default") else source
    params: dict[str, Any] = {"limit": lim}
    if src:
        params["source"] = src
    return await client.proxy_get("/api/v1/supplement/providers/smoke/runs", params=params)


@router.post("/sources/{source}/pause")
async def pause_source(source: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/sources/{source}/pause", json_body=body or {})


@router.post("/sources/{source}/resume")
async def resume_source(source: str) -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post(f"/api/v1/supplement/sources/{source}/resume")


@router.post("/movies/detail")
async def enrich_movie_detail(
    source_movie_id: str = Query(...),
    source: str = Query("avbase"),
) -> dict[str, Any]:
    client = get_info_client()
    smid = source_movie_id.default if hasattr(source_movie_id, "default") else source_movie_id
    src = source.default if hasattr(source, "default") else source
    return await client.proxy_post(
        "/api/v1/supplement/movies/detail",
        params={"source": src, "source_movie_id": smid},
    )


@router.post("/movies/detail/jobs")
async def create_movie_detail_job(
    source_movie_id: str = Query(...),
    source: str = Query("avbase"),
    actress_id: int | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    smid = source_movie_id.default if hasattr(source_movie_id, "default") else source_movie_id
    src = source.default if hasattr(source, "default") else source
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    params: dict[str, Any] = {"source": src, "source_movie_id": smid}
    if aid is not None:
        params["actress_id"] = aid
    return await client.proxy_post(
        "/api/v1/supplement/movies/detail/jobs",
        params=params,
    )


@router.post("/movies/detail/jobs/batch")
async def create_movie_detail_batch_jobs(
    source: str = Query("avbase"),
    limit: int = Query(20, ge=1, le=100),
    matched: bool | None = Query(None),
    actress_id: int | None = Query(None),
    q: str | None = Query(None),
    missing_cover: bool | None = Query(None),
    missing_runtime: bool | None = Query(None),
    missing_maker: bool | None = Query(None),
    missing_categories: bool | None = Query(None),
    max_completeness: int | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    src = source.default if hasattr(source, "default") else source
    lim = limit.default if hasattr(limit, "default") else limit
    m = matched.default if hasattr(matched, "default") else matched
    aid = actress_id.default if hasattr(actress_id, "default") else actress_id
    qv = q.default if hasattr(q, "default") else q
    mc = missing_cover.default if hasattr(missing_cover, "default") else missing_cover
    mr = missing_runtime.default if hasattr(missing_runtime, "default") else missing_runtime
    mm = missing_maker.default if hasattr(missing_maker, "default") else missing_maker
    mcat = missing_categories.default if hasattr(missing_categories, "default") else missing_categories
    maxc = max_completeness.default if hasattr(max_completeness, "default") else max_completeness
    params: dict[str, Any] = {"source": src, "limit": lim}
    if m is not None:
        params["matched"] = "true" if m else "false"
    if aid is not None:
        params["actress_id"] = aid
    if qv:
        params["q"] = qv
    if mc is not None:
        params["missing_cover"] = "true" if mc else "false"
    if mr is not None:
        params["missing_runtime"] = "true" if mr else "false"
    if mm is not None:
        params["missing_maker"] = "true" if mm else "false"
    if mcat is not None:
        params["missing_categories"] = "true" if mcat else "false"
    if maxc is not None:
        params["max_completeness"] = maxc
    return await client.proxy_post(
        "/api/v1/supplement/movies/detail/jobs/batch",
        params=params,
    )
