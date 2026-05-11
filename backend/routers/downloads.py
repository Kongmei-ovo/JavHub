from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, Dict
from database import (
    get_download_candidate,
    get_download_tasks,
    delete_download_task,
    download_candidate_stats,
    list_download_candidates,
    set_download_candidate_status,
    update_download_candidate_magnet,
    upsert_download_candidate,
)
from services.downloader import downloader_service

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])

class CreateDownloadRequest(BaseModel):
    content_id: str
    title: str
    magnet: str
    path: Optional[str] = None


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

@router.post("")
async def create_download(req: CreateDownloadRequest) -> Dict[str, Any]:
    """创建下载任务并发送到OpenList"""
    task_id = await downloader_service.create_download_task(
        code=req.content_id,
        title=req.title,
        magnet=req.magnet,
        path=req.path or "",
    )
    return {"id": task_id, "status": "downloading"}

@router.get("")
async def list_downloads() -> Dict[str, Any]:
    """获取下载列表"""
    tasks = get_download_tasks()
    return {"data": tasks, "total": len(tasks)}

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
    limit: int = 200,
) -> Dict[str, Any]:
    """下载候选列表。候选是人工确认前的安全队列。"""
    rows = list_download_candidates(
        status=status,
        actress_id=actress_id,
        source=source,
        q=q,
        limit=limit,
    )
    return {"data": rows, "total": len(rows), "stats": download_candidate_stats()}


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
    return {"status": "ok", "candidate": candidate}


@router.put("/candidates/{candidate_id}/magnet")
async def update_candidate_magnet(candidate_id: int, req: UpdateCandidateMagnetRequest) -> Dict[str, Any]:
    if not req.magnet.strip():
        raise HTTPException(status_code=400, detail="magnet is required")
    candidate = update_download_candidate_magnet(candidate_id, req.magnet.strip(), req.magnet_source)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "ok", "candidate": candidate}


@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(candidate_id: int) -> Dict[str, Any]:
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
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
        set_download_candidate_status(candidate_id, "failed")
        raise HTTPException(status_code=500, detail=f"下载任务创建失败: {exc}") from exc

    updated = set_download_candidate_status(candidate_id, "sent", download_task_id=task_id)
    return {"status": "ok", "candidate": updated, "download_task_id": task_id}


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(candidate_id: int) -> Dict[str, Any]:
    candidate = set_download_candidate_status(candidate_id, "rejected")
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "ok", "candidate": candidate}
