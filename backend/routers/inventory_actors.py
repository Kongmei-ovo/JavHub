"""Inventory actor routes."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import (
    add_actor_alias,
    find_similar_actresses,
    get_actor_aliases,
    get_actor_primary_name,
    get_canonical_actress_id,
    get_inventory_actor,
    get_inventory_actors_by_ids,
    get_inventory_videos,
    get_latest_snapshot_key,
    get_missing_videos,
    get_snapshot_actor,
    get_snapshot_actors,
    get_snapshot_actors_with_inventory_stats,
    set_actor_primary_name,
)
from services.cache import get_or_set_response, should_bypass_response_cache


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _emby_image_url(actress_id: str, image_tag: str) -> str:
    if not image_tag:
        return ""
    from config import config

    emby_cfg = getattr(config, "emby", {})
    api_url = emby_cfg.get("api_url", "").rstrip("/")
    return f"{api_url}/Items/{actress_id}/Images/Primary?tag={image_tag}"


def _actor_sort_params(actor_sort: str) -> tuple[str, str]:
    if actor_sort == "total_videos":
        return "total_videos", "desc"
    if actor_sort == "missing_count":
        return "missing_count", "desc"
    return "actress_name", "asc"


def _actor_sort_field(sort_by: str | None) -> str:
    if sort_by in {"total_videos", "missing_count"}:
        return sort_by
    return "actress_name"


def _resolve_canonical_id(actress_id: int, alias_map: dict[int, int]) -> int:
    current = actress_id
    seen: set[int] = set()
    while current in alias_map and current not in seen:
        seen.add(current)
        current = alias_map[current]
    return current


def _alias_map() -> dict[int, int]:
    aliases: dict[int, int] = {}
    for row in get_actor_aliases():
        try:
            aliases[int(row["alias_id"])] = int(row["canonical_id"])
        except (KeyError, TypeError, ValueError):
            continue
    return aliases


def _enrich_snapshot_actor(actor: dict, inventory_map: dict, alias_map: dict[int, int]) -> dict:
    actress_id = actor["actress_id"]
    canon_id = _resolve_canonical_id(int(actress_id), alias_map)
    inv = inventory_map.get(actress_id, {})
    canonical_inv = inventory_map.get(canon_id, {})
    primary = canonical_inv.get("primary_name") or ""
    image_tag = actor.get("image_tag", "")
    return {
        "actress_id": actress_id,
        "actress_name": actor["actress_name"],
        "display_name": primary or actor["actress_name"],
        "total_videos": actor.get("total_videos", 0),
        "missing_count": inv.get("missing_count", 0),
        "avatar_url": _emby_image_url(str(actress_id), image_tag),
    }


def _inventory_actors_payload(
    snapshot_key: str | None,
    search: str | None = None,
    actor_sort: str = "missing_count",
    sort_by: str | None = None,
    sort_order: str | None = None,
    page: int = 1,
    page_size: int = 60,
) -> dict:
    if not snapshot_key:
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    if sort_by is not None or sort_order is not None:
        sort_field = _actor_sort_field(sort_by)
        order = "asc" if sort_order == "asc" else "desc"
    else:
        sort_field, order = _actor_sort_params(actor_sort)
    if sort_field == "missing_count":
        result = get_snapshot_actors_with_inventory_stats(
            snapshot_key,
            search=search,
            sort_order=order,
            page=page,
            page_size=page_size,
        )
    else:
        result = get_snapshot_actors(
            snapshot_key,
            search=search,
            sort_by=sort_field,
            sort_order=order,
            page=page,
            page_size=page_size,
        )
    aliases = _alias_map()
    actor_ids = sorted({int(actor["actress_id"]) for actor in result["data"]})
    canonical_ids = sorted({_resolve_canonical_id(actor_id, aliases) for actor_id in actor_ids})
    inventory_ids = sorted({*actor_ids, *canonical_ids})
    inventory_map = {a["actress_id"]: a for a in get_inventory_actors_by_ids(inventory_ids)}
    enriched = [_enrich_snapshot_actor(actor, inventory_map, aliases) for actor in result["data"]]
    return {
        "data": enriched,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/actors")
async def list_actors(
    search: str = None,
    sort_by: str = "actress_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """List inventory actors from the latest Emby snapshot."""
    params = {
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": page_size,
    }

    async def produce() -> dict:
        return await asyncio.to_thread(
            _list_actors_payload,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

    return await get_or_set_response(
        "inventory_actors",
        params,
        produce,
        ttl=10,
        bypass=should_bypass_response_cache(cache_control),
    )


def _list_actors_payload(
    search: str = None,
    sort_by: str = "actress_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    return _inventory_actors_payload(
        snapshot_key,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


class MergeActorsRequest(BaseModel):
    from_actress_id: int
    to_actress_id: int


@router.post("/actors/merge-javhub")
def merge_actors_javhub(req: MergeActorsRequest):
    """Create a JavHub-only actor alias mapping."""
    if req.from_actress_id == req.to_actress_id:
        raise HTTPException(status_code=400, detail="不能合并到自身")
    add_actor_alias(req.from_actress_id, req.to_actress_id)
    return {"success": True, "from": req.from_actress_id, "to": req.to_actress_id, "type": "javhub_mapping"}


@router.get("/actors/find-similar")
def find_similar_actors(
    name: str = None,
    threshold: float = 0.6,
    limit: int = Query(50, ge=1, le=200),
    candidate_limit: int = Query(250, ge=2, le=1000),
):
    """Find similarly named actors."""
    bounded_limit = max(1, min(int(limit or 50), 200))
    bounded_candidate_limit = max(2, min(int(candidate_limit or 250), 1000))
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "limit": bounded_limit, "candidate_limit": bounded_candidate_limit}
    similar = find_similar_actresses(
        snapshot_key,
        name,
        threshold,
        limit=bounded_limit,
        candidate_limit=bounded_candidate_limit,
    )
    for pair in similar:
        for actor_key in ("actor_a", "actor_b"):
            actor = pair[actor_key]
            actor["avatar_url"] = _emby_image_url(str(actor["actress_id"]), actor.get("image_tag", ""))
    return {"data": similar, "limit": bounded_limit, "candidate_limit": bounded_candidate_limit}


@router.get("/actors/{actress_id}")
async def get_actor(actress_id: int):
    """Get actor detail with videos and mapping state."""
    actor = get_inventory_actor(actress_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    videos = get_inventory_videos(actress_id)
    missing = get_missing_videos(actress_id)
    canon_id = get_canonical_actress_id(actress_id)
    primary = get_actor_primary_name(canon_id)
    from database import get_confirmed_actor_mapping

    mapping = get_confirmed_actor_mapping(actress_id)

    from config import config

    emby_cfg = getattr(config, "emby", {})
    emby_api_url = emby_cfg.get("api_url", "").rstrip("/")
    emby_web_url = emby_cfg.get("web_url", "")
    if not emby_web_url and emby_api_url:
        import re

        match = re.match(r"(https?://[^:]+)", emby_api_url)
        if match:
            emby_web_url = f"{match.group(1)}:8096"

    avatar_url = ""
    emby_server_id = ""
    snapshot_key = get_latest_snapshot_key()
    if snapshot_key:
        snapshot_actor = get_snapshot_actor(snapshot_key, actress_id)
        image_tag = snapshot_actor.get("image_tag", "") if snapshot_actor else ""
        if image_tag:
            avatar_url = _emby_image_url(str(actress_id), image_tag)
        from modules.emby_client import get_emby_client

        try:
            emby = get_emby_client()
            system_info = await emby._get("/System/Info")
            emby_server_id = system_info.get("Id", "")
        except Exception:
            emby_server_id = ""

    return {
        **actor,
        "display_name": primary or actor["actress_name"],
        "videos": videos,
        "missing_videos": missing,
        "mapping_status": "confirmed" if mapping else "unmapped",
        "actor_mapping": mapping,
        "avatar_url": avatar_url,
        "_emby_api_url": emby_api_url,
        "_emby_web_url": emby_web_url,
        "_emby_server_id": emby_server_id,
    }


@router.get("/actors/{actress_id}/emby-videos")
async def get_actor_emby_videos(actress_id: int):
    """Fetch actor videos from Emby live."""
    from modules.emby_client import get_emby_client

    emby = get_emby_client()
    try:
        items = await emby.get_actress_videos(actress_id)
        videos = []
        for item in items:
            videos.append({
                "item_id": item.get("Id"),
                "title": item.get("Name"),
                "filename": item.get("FileName"),
                "production_year": item.get("ProductionYear"),
                "premiere_date": item.get("PremiereDate"),
                "image_tag": item.get("ImageTags", {}).get("Primary"),
            })
        videos.sort(key=lambda x: (x.get("production_year") or 9999, x.get("premiere_date") or ""))
        return {"data": videos, "total": len(videos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Emby影片失败: {str(e)}")


class PrimaryNameRequest(BaseModel):
    actress_id: int
    primary_name: str


@router.put("/actors/{actress_id}/primary-name")
def set_primary_name(actress_id: int, req: PrimaryNameRequest):
    """Set the primary display name for an actor."""
    set_actor_primary_name(actress_id, req.primary_name)
    return {"success": True}
