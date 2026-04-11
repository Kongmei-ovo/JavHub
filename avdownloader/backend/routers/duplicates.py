from fastapi import APIRouter, HTTPException
from typing import Any
from database import add_ignored_duplicate, is_duplicate_ignored
from modules.emby_client import get_emby_client
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])

@router.get("")
async def list_duplicates() -> dict[str, Any]:
    """获取可疑重复列表"""
    emby_client = get_emby_client()
    info_client = get_info_client()
    duplicates = await emby_client.find_duplicates(info_client)
    return {
        "data": duplicates,
        "total": len(duplicates),
    }

@router.post("/{emby_item_id}/delete")
async def delete_duplicate(emby_item_id: str) -> dict[str, Any]:
    """删除 Emby 重复条目"""
    emby_client = get_emby_client()
    success = await emby_client.delete_item(emby_item_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete from Emby")
    return {"status": "ok", "deleted": emby_item_id}

@router.post("/{emby_item_id}/ignore")
async def ignore_duplicate(emby_item_id: str) -> dict[str, Any]:
    """忽略可疑重复"""
    if is_duplicate_ignored(emby_item_id):
        return {"status": "already_ignored", "emby_item_id": emby_item_id}

    add_ignored_duplicate(None, emby_item_id, "用户忽略")
    return {"status": "ok", "emby_item_id": emby_item_id}