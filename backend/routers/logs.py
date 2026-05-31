import asyncio
from fastapi import APIRouter, Query
from database import log as log_database
from services import cache as response_cache
from services.cache import should_bypass_response_cache

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

@router.get("")
async def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
    cache_control: str | None = Query(None, alias="cache"),
):
    """
    获取日志列表
    limit: 返回数量，默认100
    level: 过滤级别 (INFO/WARNING/ERROR)
    """
    normalized_level = level.upper() if level else None
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("logs"),
        "limit": limit,
        "level": normalized_level,
        "q": q,
        "offset": offset,
    }

    async def produce():
        rows, total = await asyncio.to_thread(
            log_database.list_logs,
            limit=limit,
            level=normalized_level,
            q=q,
            offset=offset,
        )
        return {"data": rows, "total": total, "limit": limit, "offset": offset}

    return await response_cache.get_or_set_response(
        "logs",
        cache_params,
        produce,
        ttl=2,
        bypass=bypass_cache,
    )

@router.post("")
def add_log_entry(level: str, message: str):
    """写入日志"""
    log_database.add_log(level.upper(), message)
    return {"success": True}

@router.delete("")
def clear_logs():
    """清空日志"""
    log_database.clear_logs()
    return {"success": True}
