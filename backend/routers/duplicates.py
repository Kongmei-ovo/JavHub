from fastapi import APIRouter, HTTPException
from typing import Any
import re
from database import (
    add_ignored_duplicate,
    get_latest_snapshot_key,
    get_snapshot_duplicate_candidates,
    is_duplicate_ignored,
)
from modules.emby_client import get_emby_client
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/duplicates", tags=["duplicates"])

_CONTENT_ID_RE = re.compile(r"([A-Z]+-\d+)", re.IGNORECASE)


def _duplicate_key(row: dict[str, Any]) -> str | None:
    title = row.get("title") or ""
    filename = row.get("filename") or ""
    text = f"{title} {filename}".upper()
    match = _CONTENT_ID_RE.search(text)
    if match:
        return match.group(1).upper()
    normalized_title = re.sub(r"\s+", " ", title).strip().upper()
    return normalized_title or None


def _snapshot_duplicates() -> list[dict[str, Any]]:
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return []

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in get_snapshot_duplicate_candidates(snapshot_key):
        emby_item_id = str(row.get("emby_item_id") or "")
        if not emby_item_id or is_duplicate_ignored(emby_item_id):
            continue
        key = _duplicate_key(row)
        if not key:
            continue
        groups.setdefault(key, []).append({
            "emby_item_id": emby_item_id,
            "emby_name": row.get("title") or row.get("filename") or "",
            "filename": row.get("filename") or "",
        })

    duplicates = []
    for key, items in groups.items():
        unique_items = {item["emby_item_id"]: item for item in items}
        if len(unique_items) < 2:
            continue
        grouped_items = list(unique_items.values())
        duplicates.append({
            "emby_item_id": grouped_items[0]["emby_item_id"],
            "emby_name": grouped_items[0]["emby_name"],
            "content_id": key,
            "javinfo_title": grouped_items[0]["emby_name"],
            "similarity": 1,
            "reason": f"Emby 快照中同番号出现 {len(grouped_items)} 个条目",
            "duplicate_count": len(grouped_items),
            "items": grouped_items,
        })

    duplicates.sort(key=lambda item: (-item["duplicate_count"], item["content_id"]))
    return duplicates

@router.get("")
async def list_duplicates() -> dict[str, Any]:
    """获取可疑重复列表"""
    snapshot_duplicates = _snapshot_duplicates()
    if snapshot_duplicates:
        return {
            "data": snapshot_duplicates,
            "total": len(snapshot_duplicates),
        }

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
