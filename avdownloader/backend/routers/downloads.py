from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, Dict
from database import create_download_task, get_download_tasks, delete_download_task

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

class CreateDownloadRequest(BaseModel):
    content_id: str
    title: str
    magnet: str
    path: Optional[str] = None

@router.post("")
async def create_download(req: CreateDownloadRequest) -> Dict[str, Any]:
    """创建下载任务"""
    task_id = create_download_task(
        content_id=req.content_id,
        title=req.title,
        magnet=req.magnet,
        path=req.path,
    )
    return {"id": task_id, "status": "pending"}

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
