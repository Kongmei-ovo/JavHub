from fastapi import APIRouter, Query
from database import log as log_database

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

@router.get("")
async def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
):
    """
    获取日志列表
    limit: 返回数量，默认100
    level: 过滤级别 (INFO/WARNING/ERROR)
    """
    normalized_level = level.upper() if level else None
    rows, total = log_database.list_logs(limit=limit, level=normalized_level, q=q, offset=offset)
    return {"data": rows, "total": total, "limit": limit, "offset": offset}

@router.post("")
async def add_log_entry(level: str, message: str):
    """写入日志"""
    log_database.add_log(level.upper(), message)
    return {"success": True}

@router.delete("")
async def clear_logs():
    """清空日志"""
    log_database.clear_logs()
    return {"success": True}
