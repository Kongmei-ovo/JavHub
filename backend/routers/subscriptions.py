from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any
from database import add_subscription, get_subscriptions, delete_subscription

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])

class CreateSubscriptionRequest(BaseModel):
    actress_id: int
    actress_name: str
    auto_download: bool = False

@router.get("")
async def list_subscriptions() -> dict[str, Any]:
    subscriptions = get_subscriptions()
    from database import list_download_candidates
    for sub in subscriptions:
        actress_id = sub.get("actress_id")
        if not actress_id:
            sub["candidate_count"] = 0
            sub["needs_magnet_count"] = 0
            sub["mapping_status"] = "javinfo"
            continue
        rows = list_download_candidates(
            status="candidate",
            actress_id=actress_id,
            source="subscription",
            limit=100000,
        )
        sub["candidate_count"] = len(rows)
        sub["needs_magnet_count"] = sum(1 for row in rows if not row.get("magnet"))
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
    from database import get_translation
    from services.translation import _translate_item
    client = get_info_client()
    result = await client.list_actresses(q=q, page=1, page_size=20)
    matched = result.get("data", []) if isinstance(result, dict) else []
    for actress in matched:
        actress_id = actress.get("id")
        if actress_id:
            trans = get_translation(f"actress:{actress_id}")
            if trans:
                actress_map = trans.get("actress", {})
                for name_key in ["name_kanji", "name_romaji", "name_ja", "name_en", "name"]:
                    orig = actress.get(name_key)
                    if orig:
                        actress[f"{name_key}_translated"] = _translate_item(orig, actress_map)
                        break
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

@router.get("/new_movies")
async def get_new_movies() -> dict[str, Any]:
    """获取所有订阅的新片（不在 Emby 库中的），按 actress_id 分组"""
    subscriptions = get_subscriptions()
    from database import list_download_candidates

    result = {}  # {actress_id: [movies]}

    for sub in subscriptions:
        if not sub.get("enabled"):
            continue

        actress_id = sub.get("actress_id")
        if not actress_id:
            continue

        rows = list_download_candidates(
            status="candidate",
            actress_id=actress_id,
            source="subscription",
            limit=100,
        )
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

    return {"data": result}

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
