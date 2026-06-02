import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any
from database import (
    add_subscription,
    delete_subscription,
    download_candidate_counts_by_actress,
    get_subscriptions,
    list_download_candidates,
    list_download_candidates_by_actress_ids,
)
from services import cache as response_cache
from services.cache import should_bypass_response_cache

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])

class CreateSubscriptionRequest(BaseModel):
    actress_id: int
    actress_name: str
    auto_download: bool = False

@router.get("")
async def list_subscriptions(cache_control: str | None = Query(None, alias="cache")) -> dict[str, Any]:
    cache_params = {
        "subscriptions": await response_cache.get_data_generation_async("subscriptions"),
        "download_candidates": await response_cache.get_data_generation_async("download_candidates"),
    }

    async def produce() -> dict[str, Any]:
        return await asyncio.to_thread(_list_subscriptions_payload)

    return await response_cache.get_or_set_response(
        "subscriptions",
        cache_params,
        produce,
        ttl=5,
        bypass=should_bypass_response_cache(cache_control),
    )


def _list_subscriptions_payload() -> dict[str, Any]:
    subscriptions = get_subscriptions()
    counts_by_actress = download_candidate_counts_by_actress(status="candidate", source="subscription")
    for sub in subscriptions:
        actress_id = sub.get("actress_id")
        if not actress_id:
            sub["candidate_count"] = 0
            sub["needs_magnet_count"] = 0
            sub["mapping_status"] = "javinfo"
            continue
        counts = counts_by_actress.get(int(actress_id), {})
        sub["candidate_count"] = int(counts.get("candidate_count") or 0)
        sub["needs_magnet_count"] = int(counts.get("needs_magnet_count") or 0)
        # 订阅本身 already uses JavInfo actress id, so it is mapped by definition.
        sub["mapping_status"] = "javinfo"
    return {"data": subscriptions, "total": len(subscriptions)}

@router.post("")
async def create_subscription(req: CreateSubscriptionRequest) -> dict[str, Any]:
    sub_id = add_subscription(
        actress_id=req.actress_id,
        actress_name=req.actress_name,
        auto_download=req.auto_download,
    )
    return {"id": sub_id, "status": "ok"}

@router.get("/search")
async def search_actresses(q: str = Query("", min_length=1)) -> dict[str, Any]:
    """搜索演员（供前端订阅搜索用）"""
    from modules.info_client import get_info_client
    from translations import get_translator_service
    client = get_info_client()
    result = await client.list_actresses(q=q, page=1, page_size=20)
    matched = result.get("data", []) if isinstance(result, dict) else []
    await get_translator_service().translate_entities(
        matched,
        entity_type="actress",
        keys=["name_kanji", "name_romaji", "name_ja", "name_en", "name"],
        allow_network=False,
    )
    return {"data": matched, "total": len(matched)}

class ToggleSubscriptionRequest(BaseModel):
    actress_id: int
    actress_name: str
    auto_download: bool = False

@router.post("/toggle")
async def toggle_subscription_endpoint(req: ToggleSubscriptionRequest) -> dict[str, Any]:
    """切换订阅状态"""
    from database import toggle_subscription
    result = toggle_subscription(req.actress_id, req.actress_name, req.auto_download)
    return {"status": "ok", **result}

@router.get("/status/{actress_id}")
async def subscription_status(actress_id: int) -> dict[str, Any]:
    """检查某演员的订阅状态"""
    from database import is_subscribed
    return {"subscribed": is_subscribed(actress_id)}

@router.post("/check")
async def check_subscriptions() -> dict[str, Any]:
    """手动检查订阅更新"""
    from services.subscription import check_all_subscriptions_report
    return await check_all_subscriptions_report()

def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


@router.get("/new_movies")
async def get_new_movies(
    limit_per_actress: int = Query(20),
    cache_control: str | None = Query(None, alias="cache"),
) -> dict[str, Any]:
    """获取所有订阅的新片（不在 Emby 库中的），按 actress_id 分组"""
    safe_limit_per_actress = _bounded_int(limit_per_actress, 20, minimum=1, maximum=50)
    cache_params = {
        "subscriptions": await response_cache.get_data_generation_async("subscriptions"),
        "download_candidates": await response_cache.get_data_generation_async("download_candidates"),
        "limit_per_actress": safe_limit_per_actress,
    }

    async def produce() -> dict[str, Any]:
        return await asyncio.to_thread(_new_movies_payload, safe_limit_per_actress)

    return await response_cache.get_or_set_response(
        "subscription_new_movies",
        cache_params,
        produce,
        ttl=5,
        bypass=should_bypass_response_cache(cache_control),
    )


def _new_movies_payload(limit_per_actress: int = 20) -> dict[str, Any]:
    safe_limit_per_actress = _bounded_int(limit_per_actress, 20, minimum=1, maximum=50)
    subscriptions = get_subscriptions()

    result = {}  # {actress_id: [movies]}
    enabled_subscriptions = [
        sub for sub in subscriptions
        if sub.get("enabled") and sub.get("actress_id")
    ]
    rows_by_actress = list_download_candidates_by_actress_ids(
        [int(sub["actress_id"]) for sub in enabled_subscriptions],
        status="candidate",
        source="subscription",
        limit_per_actress=safe_limit_per_actress,
    )

    for sub in enabled_subscriptions:
        actress_id = int(sub["actress_id"])
        rows = rows_by_actress.get(actress_id, [])
        if rows:
            result[actress_id] = [
                {
                    "candidate_id": row.get("id"),
                    "content_id": row.get("content_id"),
                    "dvd_id": row.get("dvd_id"),
                    "title_en": row.get("title"),
                    "title_ja": row.get("title"),
                    "release_date": row.get("release_date"),
                    "jacket_thumb_url": row.get("jacket_thumb_url"),
                }
                for row in rows
            ]

    return {
        "data": result,
        "limit_per_actress": safe_limit_per_actress,
    }

class UpdateSubscriptionRequest(BaseModel):
    enabled: bool | None = None
    auto_download: bool | None = None

@router.delete("/{subscription_id}")
async def remove_subscription(subscription_id: int) -> dict[str, Any]:
    delete_subscription(subscription_id)
    return {"status": "ok"}

@router.put("/{subscription_id}")
async def update_subscription_endpoint(subscription_id: int, req: UpdateSubscriptionRequest) -> dict[str, Any]:
    """更新订阅设置"""
    from database import update_subscription
    kwargs = {}
    if req.enabled is not None:
        kwargs["enabled"] = req.enabled
    if req.auto_download is not None:
        kwargs["auto_download"] = req.auto_download
    update_subscription(subscription_id, **kwargs)
    return {"status": "ok"}

@router.post("/{subscription_id}/check")
async def check_single_subscription(subscription_id: int) -> dict[str, Any]:
    """手动检查单条订阅"""
    from services.subscription import check_single_subscription
    result = await check_single_subscription(subscription_id)
    if result is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return {"status": "ok", **result}
