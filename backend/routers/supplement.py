from __future__ import annotations
import logging
from typing import Any
from fastapi import APIRouter, Query
from modules.info_client import _transform_jacket_url, get_info_client
from routers._query import qv
from services.supplement_candidates import (
    generate_download_candidates_from_catalog,
    generate_download_candidates_from_supplement,
)
from translations import get_translator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supplement", tags=["supplement"])


def _transform_movie_cover(movie: Any) -> None:
    """In-place: turn relative catalog (javinfo) jacket paths into full DMM URLs.

    Matched movies now borrow their cover from the local catalog, whose jacket
    columns store DMM-relative paths. ``_transform_jacket_url`` passes http URLs
    through untouched, so 鸡源/蛋源 covers are unaffected.
    """
    if not isinstance(movie, dict):
        return
    for key in ("cover_url", "cover_thumb_url"):
        if movie.get(key):
            movie[key] = _transform_jacket_url(movie[key])


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
    src = qv(source)
    return await client.proxy_get(
        f"/api/v1/supplement/actresses/{actress_id}/status",
        params={"source": src},
    )


@router.post("/actresses/ensure_subscribed")
async def ensure_subscribed_actresses() -> dict[str, Any]:
    """为所有启用的演员订阅触发补全（filmography job + resolved refresh）。

    后台逐个调用 supplement autopilot（自带 TTL 去重，JavInfoApi 侧还有
    active-job 去重），立即返回排期数量。供运营总览数据管道卡使用。
    """
    import asyncio

    from database import get_subscriptions
    from services.supplement_autopilot import ensure_actress_supplement

    actress_ids: list[int] = []
    for sub in get_subscriptions():
        if not sub.get("enabled"):
            continue
        scope = str(sub.get("scope") or "actress").strip().lower()
        if scope != "actress":
            continue
        target = sub.get("target_id") or sub.get("actress_id")
        if target:
            actress_ids.append(int(target))

    async def run() -> None:
        for actress_id in actress_ids:
            await ensure_actress_supplement(actress_id)

    if actress_ids:
        asyncio.get_running_loop().create_task(run())
    return {"scheduled": len(actress_ids)}


@router.post("/actresses/{actress_id}/filmography/jobs")
async def create_filmography_job(
    actress_id: int,
    source: str = Query("avbase"),
) -> dict[str, Any]:
    client = get_info_client()
    src = qv(source)
    return await client.proxy_post(
        f"/api/v1/supplement/actresses/{actress_id}/filmography/jobs",
        params={"source": src},
    )


@router.post("/avatars/gfriends/jobs")
async def create_gfriends_avatar_sync_job() -> dict[str, Any]:
    client = get_info_client()
    return await client.proxy_post("/api/v1/supplement/avatars/gfriends/jobs")


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
    error_provider: str | None = Query(None),
    error_reason: str | None = Query(None),
) -> dict[str, Any]:
    client = get_info_client()
    p = qv(page)
    ps = qv(page_size)
    src = qv(source)
    st = qv(status)
    aid = qv(actress_id)
    ep = qv(error_provider)
    er = qv(error_reason)
    params: dict[str, Any] = {"page": p, "page_size": ps}
    if src:
        params["source"] = src
    if st:
        params["status"] = st
    if aid is not None:
        params["actress_id"] = aid
    if ep:
        params["error_provider"] = ep
    if er:
        params["error_reason"] = er
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
    otm = qv(older_than_minutes)
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
    p = qv(page)
    ps = qv(page_size)
    m = qv(matched)
    src = qv(source)
    aid = qv(actress_id)
    query_value = qv(q)
    mc = qv(missing_cover)
    mr = qv(missing_runtime)
    mm = qv(missing_maker)
    mcat = qv(missing_categories)
    maxc = qv(max_completeness)
    params: dict[str, Any] = {"page": p, "page_size": ps}
    if m is not None:
        params["matched"] = "true" if m else "false"
    if src:
        params["source"] = src
    if aid is not None:
        params["actress_id"] = aid
    if query_value:
        params["q"] = query_value
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
    result = await client.proxy_get("/api/v1/supplement/movies", params=params)
    if isinstance(result, dict):
        for movie in result.get("data") or []:
            _transform_movie_cover(movie)
    return result


@router.get("/movies/{movie_id}/sources")
async def get_movie_sources(movie_id: int) -> dict[str, Any]:
    client = get_info_client()
    data = await client.proxy_get(f"/api/v1/supplement/movies/{movie_id}/sources")
    if isinstance(data, dict):
        _transform_movie_cover(data.get("movie"))
        for bucket in ("chosen_fields", "field_values"):
            for field in data.get(bucket) or []:
                if (
                    isinstance(field, dict)
                    and field.get("field_name") in ("cover_url", "cover_thumb_url")
                    and field.get("field_value")
                ):
                    field["field_value"] = _transform_jacket_url(field["field_value"])
    return await get_translator_service().translate_supplement_sources(data, allow_network=False)


@router.post("/movies/candidates")
async def create_download_candidates_from_supplement(
    actress_id: int | None = Query(None),
    actress_name: str = Query(""),
    source: str | None = Query(None),
    q: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=2000),
    matched: bool | None = Query(False),
    missing_cover: bool | None = Query(None),
    missing_runtime: bool | None = Query(None),
    missing_maker: bool | None = Query(None),
    missing_categories: bool | None = Query(None),
    max_completeness: int | None = Query(None),
) -> dict[str, Any]:
    aid = qv(actress_id)
    name = qv(actress_name)
    src = qv(source)
    query_value = qv(q)
    lim = qv(limit)
    m = qv(matched)
    mc = qv(missing_cover)
    mr = qv(missing_runtime)
    mm = qv(missing_maker)
    mcat = qv(missing_categories)
    maxc = qv(max_completeness)
    result = await generate_download_candidates_from_supplement(
        actress_id=aid,
        actress_name=name,
        supplement_source=src,
        q=query_value,
        limit=lim,
        matched=m,
        missing_cover=mc,
        missing_runtime=mr,
        missing_maker=mm,
        missing_categories=mcat,
        max_completeness=maxc,
    )
    return {"status": "ok", **result}


@router.post("/actresses/{actress_id}/candidates")
async def create_download_candidates_from_actress_catalog(
    actress_id: int,
    actress_name: str = Query(""),
    canonical_number: str = Query(""),
    limit: int | None = Query(None, ge=1, le=5000),
) -> dict[str, Any]:
    """Create candidates from the canonical funnel shown in the actress UI.

    Unlike ``/movies/candidates``, this includes native catalog films that do
    not yet have a ``supplement_movies`` row, so the displayed source-stage
    count and the batch action operate on the same set.
    """
    import asyncio

    from routers.film_dictionary import get_actress_completeness

    # A batch action must use the current funnel, not a response cached before
    # the previous job/candidate transition.
    data = await get_actress_completeness(actress_id, cache_control="0")
    result = await asyncio.to_thread(
        generate_download_candidates_from_catalog,
        data.get("films") or [],
        actress_id=actress_id,
        actress_name=qv(actress_name) or "",
        canonical_number=qv(canonical_number) or "",
        limit=qv(limit),
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
    lim = qv(limit)
    src = qv(source)
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


@router.post("/sources/{source}/check")
async def check_source(source: str) -> dict[str, Any]:
    """对来源即时探活并回写健康（可达则恢复 / 故障则降级）。供来源健康的「检查」/「全局检查」按钮。

    探活会真正发一次请求（含 Cloudflare 过盾）。单源最长 ~90s；`source=all` 时后端以
    受限并发探活全部来源、整体上限 4 分钟，故 long 客户端超时按 source 放宽。
    """
    client = get_info_client()
    timeout = 300 if source.strip().lower() == "all" else 120
    return await client.proxy_post_long(
        f"/api/v1/supplement/sources/{source}/check",
        timeout=timeout,
    )


@router.post("/movies/detail")
async def enrich_movie_detail(
    source_movie_id: str = Query(...),
    source: str = Query("avbase"),
    sync: bool = Query(False),
) -> dict[str, Any]:
    client = get_info_client()
    smid = qv(source_movie_id)
    src = qv(source)
    sync_value = qv(sync)
    if not sync_value:
        return await client.proxy_post(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": src, "source_movie_id": smid},
        )
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
    smid = qv(source_movie_id)
    src = qv(source)
    aid = qv(actress_id)
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
    src = qv(source)
    lim = qv(limit)
    m = qv(matched)
    aid = qv(actress_id)
    query_value = qv(q)
    mc = qv(missing_cover)
    mr = qv(missing_runtime)
    mm = qv(missing_maker)
    mcat = qv(missing_categories)
    maxc = qv(max_completeness)
    params: dict[str, Any] = {"source": src, "limit": lim}
    if m is not None:
        params["matched"] = "true" if m else "false"
    if aid is not None:
        params["actress_id"] = aid
    if query_value:
        params["q"] = query_value
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


@router.post("/actresses/{actress_id}/fields/enrich")
async def enrich_actress_fields(
    actress_id: int,
    source: str = Query("all"),
    limit: int | None = Query(None, ge=1, le=5000),
) -> dict[str, Any]:
    """一键补字段：为该演员所有「缺字段」(funnel_stage=meta_gap) 的 canonical 番号
    各排一个蛋源 detail job（默认全部源），免去补全页字段阶段逐部点「补字段」。

    番号来自 completeness（与字段阶段所见同源），一次提交给 JavInfoApi 的持久队列。
    只有所有 queued/existing 结果确认落库后才返回，避免 Web 进程重启或快速刷新时
    丢掉尚未发送的后半批任务。
    """
    from routers.film_dictionary import get_actress_completeness

    src = qv(source) or "all"
    lim = qv(limit)

    data = await get_actress_completeness(actress_id, cache_control="0")
    numbers = [
        film["canonical_number"]
        for film in (data.get("films") or [])
        if film.get("funnel_stage") == "meta_gap" and film.get("canonical_number")
    ]
    if lim:
        numbers = numbers[:lim]

    if not numbers:
        return {"requested": 0, "scheduled": 0, "queued": 0, "existing": 0, "skipped": 0, "job_ids": []}

    result = await get_info_client().proxy_post(
        "/api/v1/supplement/movies/detail/jobs/batch",
        json_body={"source_movie_ids": numbers, "actress_id": actress_id},
        params={"source": src},
    )
    queued = int(result.get("queued") or 0)
    return {
        "requested": len(numbers),
        # Backwards-compatible response key; unlike the old implementation it
        # now counts jobs confirmed as newly queued rather than merely observed.
        "scheduled": queued,
        **result,
    }
