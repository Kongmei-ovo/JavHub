import asyncio
import time
from fastapi import APIRouter, HTTPException
from fastapi import Query
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
from services.cache import (
    get_data_generation_async,
    get_or_set_response,
    set_data_generation,
    should_bypass_response_cache,
)

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


def _snapshot_duplicates_for_key(snapshot_key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in get_snapshot_duplicate_candidates(snapshot_key):
        emby_item_id = str(row.get("emby_item_id") or "")
        if not emby_item_id:
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


def _snapshot_duplicates_payload() -> tuple[str | None, list[dict[str, Any]]]:
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return None, []
    return snapshot_key, _snapshot_duplicates_for_key(snapshot_key)


def _snapshot_duplicates() -> list[dict[str, Any]]:
    _snapshot_key, duplicates = _snapshot_duplicates_payload()
    return duplicates

@router.get("")
async def list_duplicates(
    live: bool = False,
    cache_control: str | None = Query(None, alias="cache"),
) -> dict[str, Any]:
    """获取可疑重复列表"""
    bypass_cache = should_bypass_response_cache(cache_control)

    async def produce_snapshot() -> dict[str, Any]:
        snapshot_key, snapshot_duplicates = await asyncio.to_thread(_snapshot_duplicates_payload)
        if snapshot_key:
            return {
                "data": snapshot_duplicates,
                "total": len(snapshot_duplicates),
                "source": "snapshot",
                "snapshot_key": snapshot_key,
            }
        return {
            "data": [],
            "total": 0,
            "source": "snapshot",
            "snapshot_key": None,
            "live_scan_available": True,
        }

    snapshot_result = await get_or_set_response(
        "duplicates_snapshot",
        {"generation": await get_data_generation_async("duplicates")},
        produce_snapshot,
        ttl=10,
        bypass=bypass_cache,
    )
    if snapshot_result.get("snapshot_key") or not live:
        return snapshot_result

    async def produce() -> dict[str, Any]:
        emby_client = get_emby_client()
        info_client = get_info_client()
        live_duplicates = await emby_client.find_duplicates(info_client)
        return {
            "data": live_duplicates,
            "total": len(live_duplicates),
            "source": "live",
            "snapshot_key": None,
        }

    generation = await get_data_generation_async("duplicates")
    return await get_or_set_response(
        "duplicates_live",
        {"generation": generation},
        produce,
        ttl=300,
        bypass=bypass_cache,
    )

@router.post("/{emby_item_id}/delete")
async def delete_duplicate(emby_item_id: str) -> dict[str, Any]:
    """删除 Emby 重复条目"""
    emby_client = get_emby_client()
    success = await emby_client.delete_item(emby_item_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete from Emby")
    set_data_generation("duplicates", int(time.time()))
    return {"status": "ok", "deleted": emby_item_id}

@router.post("/{emby_item_id}/ignore")
async def ignore_duplicate(emby_item_id: str) -> dict[str, Any]:
    """忽略可疑重复"""
    if is_duplicate_ignored(emby_item_id):
        return {"status": "already_ignored", "emby_item_id": emby_item_id}

    add_ignored_duplicate(None, emby_item_id, "用户忽略")
    set_data_generation("duplicates", int(time.time()))
    return {"status": "ok", "emby_item_id": emby_item_id}
