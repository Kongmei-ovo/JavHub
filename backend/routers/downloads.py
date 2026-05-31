import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional, Dict
from database import (
    add_download_candidate_event,
    bulk_set_download_candidate_status,
    count_download_candidates,
    get_download_candidate,
    get_download_tasks,
    delete_download_task,
    download_candidate_stats,
    download_candidate_summary,
    download_candidate_summary_with_sources,
    list_candidate_process_runs,
    list_download_candidates,
    list_download_candidates_page,
    set_download_candidate_status,
    update_download_candidate_magnet,
    upsert_download_candidate,
)
from services.downloader import downloader_service
from services.downloaders import (
    get_downloaders_config,
    save_downloaders_config,
    test_downloader_config,
)
from services.candidate_processor import (
    enrich_candidate_magnet,
    preview_candidates,
    process_candidate,
    process_candidates,
    retry_failed_candidates_from_run,
)
from services import cache as response_cache
from services.cache import should_bypass_response_cache

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])

class CreateDownloadRequest(BaseModel):
    content_id: str
    title: str
    magnet: str
    path: Optional[str] = None
    downloader_id: Optional[str] = None


class DownloaderClientRequest(BaseModel):
    id: Optional[str] = None
    type: str = "openlist"
    name: Optional[str] = None
    enabled: bool = True
    address: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    default_path: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    paused: bool = False
    timeout: Optional[int] = None


class DownloadersConfigRequest(BaseModel):
    default_id: Optional[str] = None
    clients: list[DownloaderClientRequest] = []


class CreateCandidateRequest(BaseModel):
    content_id: str
    dvd_id: Optional[str] = None
    title: Optional[str] = None
    actress_id: Optional[int] = None
    actress_name: Optional[str] = None
    jacket_thumb_url: Optional[str] = None
    release_date: Optional[str] = None
    source: str = "manual"
    reason: Optional[str] = None
    magnet: Optional[str] = None


class UpdateCandidateMagnetRequest(BaseModel):
    magnet: str
    magnet_source: str = "manual"


class BulkCandidateRequest(BaseModel):
    ids: list[int]


class ProcessCandidateRequest(BaseModel):
    policy: Optional[str] = None
    enrich: bool = True
    force: bool = False


class ProcessCandidatesRequest(BaseModel):
    policy: Optional[str] = None
    enrich: bool = True
    force: bool = False
    dry_run: bool = False
    status: Optional[str] = "candidate"
    actress_id: Optional[int] = None
    source: Optional[str] = None
    q: Optional[str] = None
    needs_magnet: Optional[bool] = None
    limit: int = 50


class RetryCandidateRunRequest(BaseModel):
    enrich: bool = True
    force: bool = False

@router.post("")
async def create_download(req: CreateDownloadRequest) -> Dict[str, Any]:
    """创建下载任务并发送到默认或指定下载器"""
    task_id = await downloader_service.create_download_task(
        code=req.content_id,
        title=req.title,
        magnet=req.magnet,
        path=req.path or "",
        downloader_id=req.downloader_id or "",
    )
    return {"id": task_id, "status": "downloading"}

@router.get("")
async def list_downloads(cache_control: Optional[str] = Query(None, alias="cache")) -> Dict[str, Any]:
    """获取下载列表"""
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {"generation": await response_cache.get_data_generation_async("download_tasks")}

    async def produce() -> Dict[str, Any]:
        tasks = await asyncio.to_thread(get_download_tasks)
        return {"data": tasks, "total": len(tasks)}

    return await response_cache.get_or_set_response(
        "download_tasks",
        cache_params,
        produce,
        ttl=5,
        bypass=bypass_cache,
    )


@router.get("/downloaders")
async def list_downloaders() -> Dict[str, Any]:
    return get_downloaders_config(include_sensitive=False)


@router.put("/downloaders")
async def update_downloaders(req: DownloadersConfigRequest) -> Dict[str, Any]:
    data = save_downloaders_config(req.model_dump())
    return {"status": "ok", **data}


@router.post("/downloaders/test")
async def test_downloader(req: DownloaderClientRequest) -> Dict[str, Any]:
    result = await test_downloader_config(req.model_dump())
    return {"ok": result.success, "message": result.message, "remote_task_id": result.remote_task_id}


@router.delete("/{task_id}")
async def remove_download(task_id: int) -> Dict[str, Any]:
    """删除下载任务"""
    delete_download_task(task_id)
    return {"status": "ok"}


@router.get("/candidates")
async def list_candidates(
    status: Optional[str] = None,
    actress_id: Optional[int] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    needs_magnet: Optional[bool] = None,
    limit: int = 200,
    page: int = 1,
    page_size: Optional[int] = None,
    include_stats: bool = False,
    cache_control: Optional[str] = Query(None, alias="cache"),
) -> Dict[str, Any]:
    """下载候选列表。候选是人工确认前的安全队列。"""
    size = max(1, min(int(page_size or limit or 200), 200))
    current_page = max(1, int(page or 1))
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("download_candidates"),
        "status": status,
        "actress_id": actress_id,
        "source": source,
        "q": q,
        "needs_magnet": needs_magnet,
        "page": current_page,
        "page_size": size,
        "include_stats": include_stats,
    }

    async def produce() -> Dict[str, Any]:
        page_result = await asyncio.to_thread(
            list_download_candidates_page,
            status=status,
            actress_id=actress_id,
            source=source,
            q=q,
            needs_magnet=needs_magnet,
            limit=size,
            offset=(current_page - 1) * size,
            include_stats=include_stats,
        )
        total = int(page_result["total"] or 0)
        total_pages = max(1, (total + size - 1) // size)
        result = {
            "data": page_result["data"],
            "total": total,
            "page": current_page,
            "page_size": size,
            "total_pages": total_pages,
        }
        if include_stats and "stats" in page_result:
            result["stats"] = page_result["stats"]
        return result

    return await response_cache.get_or_set_response(
        "download_candidates_page",
        cache_params,
        produce,
        ttl=5,
        bypass=bypass_cache,
    )


@router.get("/candidates/summary")
async def candidate_summary(
    status: Optional[str] = None,
    actress_id: Optional[int] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    needs_magnet: Optional[bool] = None,
    include_sources: bool = False,
    cache_control: Optional[str] = Query(None, alias="cache"),
) -> Dict[str, Any]:
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("download_candidates"),
        "status": status,
        "actress_id": actress_id,
        "source": source,
        "q": q,
        "needs_magnet": needs_magnet,
        "include_sources": include_sources,
    }

    async def produce() -> Dict[str, Any]:
        summary_func = download_candidate_summary_with_sources if include_sources else download_candidate_summary
        return await asyncio.to_thread(
            summary_func,
            status=status,
            actress_id=actress_id,
            source=source,
            q=q,
            needs_magnet=needs_magnet,
        )

    return await response_cache.get_or_set_response(
        "download_candidates_summary",
        cache_params,
        produce,
        ttl=5,
        bypass=bypass_cache,
    )


@router.get("/candidates/runs")
def list_candidate_runs(limit: int = 20) -> Dict[str, Any]:
    limit = max(1, min(int(limit or 20), 100))
    rows = list_candidate_process_runs(limit=limit)
    return {"data": rows, "total": len(rows)}


@router.post("/candidates/runs/{run_id}/retry-failed")
async def retry_candidate_run_failed(
    run_id: int,
    req: RetryCandidateRunRequest | None = None,
) -> Dict[str, Any]:
    body = req or RetryCandidateRunRequest()
    result = await retry_failed_candidates_from_run(
        run_id,
        enrich=body.enrich,
        force=body.force,
        operator="manual",
    )
    if result.get("action") == "not_found":
        raise HTTPException(status_code=404, detail="Candidate process run not found")
    return result


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int) -> Dict[str, Any]:
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"data": candidate}


@router.post("/candidates")
async def create_candidate(req: CreateCandidateRequest) -> Dict[str, Any]:
    candidate = upsert_download_candidate(
        content_id=req.content_id,
        dvd_id=req.dvd_id,
        title=req.title,
        actress_id=req.actress_id,
        actress_name=req.actress_name,
        jacket_thumb_url=req.jacket_thumb_url,
        release_date=req.release_date,
        source=req.source,
        reason=req.reason,
        magnet=req.magnet,
        magnet_source="manual" if req.magnet else None,
    )
    add_download_candidate_event(candidate["id"], "upsert", req.reason or req.source, "manual")
    return {"status": "ok", "candidate": candidate}


@router.put("/candidates/{candidate_id}/magnet")
async def update_candidate_magnet(candidate_id: int, req: UpdateCandidateMagnetRequest) -> Dict[str, Any]:
    if not req.magnet.strip():
        raise HTTPException(status_code=400, detail="magnet is required")
    candidate = update_download_candidate_magnet(candidate_id, req.magnet.strip(), req.magnet_source)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    add_download_candidate_event(candidate_id, "magnet_updated", req.magnet_source, "manual")
    return {"status": "ok", "candidate": candidate}


@router.post("/candidates/bulk/reject")
async def bulk_reject_candidates(req: BulkCandidateRequest) -> Dict[str, Any]:
    result = bulk_set_download_candidate_status(
        req.ids,
        "rejected",
        allowed_current_statuses={"candidate", "failed"},
    )
    for candidate_id in result["ids"]:
        add_download_candidate_event(candidate_id, "bulk_rejected", "bulk action", "manual")
    return {"status": "ok", **result}


@router.post("/candidates/bulk/restore")
async def bulk_restore_candidates(req: BulkCandidateRequest) -> Dict[str, Any]:
    result = bulk_set_download_candidate_status(
        req.ids,
        "candidate",
        allowed_current_statuses={"failed", "rejected"},
    )
    for candidate_id in result["ids"]:
        add_download_candidate_event(candidate_id, "bulk_restored", "bulk action", "manual")
    return {"status": "ok", **result}


@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(candidate_id: int) -> Dict[str, Any]:
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate.get("status") == "sent":
        raise HTTPException(status_code=409, detail="候选已下发，不能重复批准")
    if candidate.get("status") == "rejected":
        raise HTTPException(status_code=409, detail="候选已拒绝，不能批准")
    magnet = (candidate.get("magnet") or "").strip()
    if not magnet:
        raise HTTPException(status_code=400, detail="候选缺少 magnet，不能下发下载")

    try:
        task_id = await downloader_service.create_download_task(
            code=candidate.get("content_id") or candidate.get("dvd_id") or "",
            title=candidate.get("title") or candidate.get("content_id") or "",
            magnet=magnet,
            path="",
        )
    except Exception as exc:
        set_download_candidate_status(candidate_id, "failed", error_msg=str(exc))
        add_download_candidate_event(candidate_id, "approve_failed", str(exc), "manual")
        raise HTTPException(status_code=500, detail=f"下载任务创建失败: {exc}") from exc

    updated = set_download_candidate_status(candidate_id, "sent", download_task_id=task_id)
    add_download_candidate_event(candidate_id, "approved", f"download_task_id={task_id}", "manual")
    return {"status": "ok", "candidate": updated, "download_task_id": task_id}


@router.post("/candidates/{candidate_id}/enrich-magnet")
async def enrich_candidate_magnet_endpoint(candidate_id: int) -> Dict[str, Any]:
    result = await enrich_candidate_magnet(candidate_id, operator="manual")
    if result.get("action") == "not_found":
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


@router.post("/candidates/{candidate_id}/process")
async def process_candidate_endpoint(
    candidate_id: int,
    req: ProcessCandidateRequest | None = None,
) -> Dict[str, Any]:
    body = req or ProcessCandidateRequest()
    result = await process_candidate(
        candidate_id,
        policy=body.policy,
        enrich=body.enrich,
        force=body.force,
        operator="manual",
    )
    if result.get("action") == "not_found":
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


@router.post("/candidates/process")
async def process_candidates_endpoint(req: ProcessCandidatesRequest | None = None) -> Dict[str, Any]:
    body = req or ProcessCandidatesRequest()
    limit = max(1, min(int(body.limit or 50), 200))
    filters = {
        "status": body.status or "candidate",
        "actress_id": body.actress_id,
        "source": body.source,
        "q": body.q,
        "needs_magnet": body.needs_magnet,
    }
    if body.dry_run:
        return await preview_candidates(
            filters=filters,
            policy=body.policy,
            enrich=body.enrich,
            limit=limit,
            force=body.force,
        )
    return await process_candidates(
        filters=filters,
        policy=body.policy,
        enrich=body.enrich,
        limit=limit,
        force=body.force,
        operator="manual",
    )


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(candidate_id: int) -> Dict[str, Any]:
    existing = get_download_candidate(candidate_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if existing.get("status") == "sent":
        raise HTTPException(status_code=409, detail="候选已下发，不能拒绝")
    candidate = set_download_candidate_status(candidate_id, "rejected")
    add_download_candidate_event(candidate_id, "rejected", "single action", "manual")
    return {"status": "ok", "candidate": candidate}
