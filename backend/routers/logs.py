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
    trace_id: str | None = None,
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
    if trace_id:
        cache_params["trace_id"] = trace_id

    async def produce():
        kwargs = {
            "limit": limit,
            "level": normalized_level,
            "q": q,
            "offset": offset,
        }
        if trace_id:
            kwargs["trace_id"] = trace_id
        rows, total = await asyncio.to_thread(log_database.list_logs, **kwargs)
        result = {"data": rows, "total": total, "limit": limit, "offset": offset}
        if trace_id:
            result["trace_id"] = trace_id
        return result

    return await response_cache.get_or_set_response(
        "logs",
        cache_params,
        produce,
        ttl=2,
        bypass=bypass_cache,
    )

@router.get("/summary")
async def get_log_summary(
    since_minutes: int = Query(1440, ge=0, le=10080),
    cache_control: str | None = Query(None, alias="cache"),
):
    """近窗日志等级计数 —— 给「系统监控」总览的「近期告警」卡用。

    since_minutes=0 表示全量；默认 1440（近 24h），上限 10080（近 7 天）。
    复用 logs 缓存命名空间与 generation，清空日志会一并失效。
    """
    window = since_minutes if since_minutes > 0 else None
    bypass_cache = should_bypass_response_cache(cache_control)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("logs"),
        "summary": True,
        "since_minutes": since_minutes,
    }

    async def produce():
        counts = await asyncio.to_thread(log_database.count_by_level, window)
        return {"counts": counts, "since_minutes": since_minutes}

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
