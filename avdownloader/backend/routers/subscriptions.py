from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from database import add_subscription, get_subscriptions, delete_subscription

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

class CreateSubscriptionRequest(BaseModel):
    actress_id: int
    actress_name: str
    auto_download: bool = False

@router.get("")
async def list_subscriptions() -> dict[str, Any]:
    subscriptions = get_subscriptions()
    return {"data": subscriptions, "total": len(subscriptions)}

@router.post("")
async def create_subscription(req: CreateSubscriptionRequest) -> dict[str, Any]:
    sub_id = add_subscription(
        actress_id=req.actress_id,
        actress_name=req.actress_name,
        auto_download=req.auto_download,
    )
    return {"id": sub_id, "status": "ok"}

@router.delete("/{subscription_id}")
async def remove_subscription(subscription_id: int) -> dict[str, Any]:
    delete_subscription(subscription_id)
    return {"status": "ok"}

@router.post("/check")
async def check_subscriptions() -> dict[str, Any]:
    """手动检查订阅更新"""
    # TODO: 调用 SubscriptionService.check_all()
    return {"status": "ok", "new_found": 0}