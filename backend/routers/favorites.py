import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import favorite
from modules.info_client import get_info_client
from routers._query import qv
from services import cache as response_cache
from services.cache import should_bypass_response_cache
from services.video_variant_index import apply_indexed_variant_groups
from services.video_variants import enrich_video_variants
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/favorites", tags=["Favorites"])


def _overlay_favorite_film_counts(items):
    """Show the 拟合后 canonical 影片数 for actress favorites instead of the raw
    商品 count captured in their stored metadata. Best-effort, in place."""
    if not isinstance(items, list):
        return items
    pairs = []  # (metadata_dict, actress_id)
    for item in items:
        if not isinstance(item, dict) or item.get("entity_type") != "actress":
            continue
        meta = item.get("metadata")
        eid = str(item.get("entity_id") or "").strip()
        if isinstance(meta, dict) and eid.isdigit():
            pairs.append((meta, int(eid)))
    if not pairs:
        return items
    try:
        from database.actress_film_count import get_actress_film_counts
        counts = get_actress_film_counts([aid for _, aid in pairs])
    except Exception:  # noqa: BLE001 - never break the favorites listing
        return items
    for meta, aid in pairs:
        if aid in counts:
            meta["movie_count"] = counts[aid]
    return items

class ToggleFavoriteRequest(BaseModel):
    entity_type: str
    entity_id: str
    metadata: Optional[Dict] = None

class FavoriteItem(BaseModel):
    entity_type: str
    entity_id: str
    metadata: Dict
    created_at: str

class CollectionItem(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str

class CollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None


@router.get("")
async def get_favorites(
    entity_type: Optional[str] = Query(None),
    include_metadata: bool = Query(False),
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """获取收藏列表；默认只返回全局状态需要的轻量索引。"""
    entity_type_value = qv(entity_type)
    include_metadata_value = bool(qv(include_metadata))
    cache_control_value = qv(cache_control)
    bypass_cache = should_bypass_response_cache(cache_control_value)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("favorites"),
        "entity_type": entity_type_value,
        "include_metadata": include_metadata_value,
    }

    async def produce():
        loader = favorite.list_favorites if include_metadata_value else favorite.list_favorite_index
        items = await asyncio.to_thread(loader, entity_type_value)
        _overlay_favorite_film_counts(items)
        return items

    return await response_cache.get_or_set_response(
        "favorites",
        cache_params,
        produce,
        ttl=5,
        bypass=bypass_cache,
    )


@router.get("/videos")
async def get_favorite_videos(cache_control: Optional[str] = Query(None, alias="cache")):
    """获取 video 类型收藏的完整影片数据（JavInfoApi + 翻译）"""
    cache_params = {"generation": await response_cache.get_data_generation_async("favorites")}

    async def produce():
        return await _favorite_videos_payload()

    return await response_cache.get_or_set_response(
        "favorite_videos",
        cache_params,
        produce,
        ttl=10,
        bypass=should_bypass_response_cache(cache_control),
    )


@router.get("/videos/page")
async def get_favorite_videos_page(
    limit: int = Query(48, ge=1, le=200),
    offset: int = Query(0),
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """分页获取 video 收藏详情，避免收藏页一次 fanout 所有 JavInfo 请求。"""
    limit_value = max(1, min(int(qv(limit) or 48), 200))
    offset_value = max(0, int(qv(offset) or 0))
    cache_control_value = qv(cache_control)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("favorites"),
        "limit": limit_value,
        "offset": offset_value,
    }

    async def produce():
        page = await asyncio.to_thread(
            favorite.list_favorites_page,
            "video",
            limit=limit_value,
            offset=offset_value,
            include_metadata=True,
        )
        data = await _favorite_videos_payload(page["data"])
        return {
            "data": data,
            "total": page["total"],
            "limit": page["limit"],
            "offset": page["offset"],
            "has_more": page["offset"] + len(data) < page["total"],
        }

    return await response_cache.get_or_set_response(
        "favorite_videos_page",
        cache_params,
        produce,
        ttl=10,
        bypass=should_bypass_response_cache(cache_control_value),
    )


async def _favorite_videos_payload(items=None):
    if items is None:
        items = await asyncio.to_thread(favorite.list_favorites, "video")
    if not items:
        return []

    client = get_info_client()
    translator = get_translator_service()

    async def fetch_one(item):
        metadata = item.get("metadata") or {}
        content_id = metadata.get("content_id") or metadata.get("dvd_id") or str(item["entity_id"]).split("::", 1)[0]
        service_code = metadata.get("service_code") or None
        try:
            data = await client.get_video(content_id, service_code=service_code)
            data = await translator.translate_video(content_id, data, allow_network=False)
            data["_favorite_entity_id"] = item["entity_id"]
            data["_created_at"] = item["created_at"]
            return data
        except Exception as e:
            return {
                "content_id": content_id,
                "dvd_id": content_id,
                "service_code": service_code,
                "_favorite_entity_id": item["entity_id"],
                "title_ja": content_id,
                "_created_at": item["created_at"],
                "_error": str(e),
            }

    sem = asyncio.Semaphore(8)
    async def limited_fetch(item):
        async with sem:
            return await fetch_one(item)
    results = await asyncio.gather(*[limited_fetch(item) for item in items])
    results.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
    # Group-favorites store one row per storefront version; collapse them to
    # one card per work so the favorites page mirrors the actress page.
    results = enrich_video_variants(results, variant_mode="grouped", include_explanations=True)
    results = apply_indexed_variant_groups(results, include_explanations=True)
    return results

def _video_group_members(entity_id: str, metadata: Optional[Dict]) -> list[tuple[str, Dict]] | None:
    """Resolve every storefront version of the work behind a video entity_id.

    Uses the materialized variant index. Returns [(entity_id, metadata), ...]
    for the whole group, or None when the video has no indexed group (single
    version, or index not built yet) — caller falls back to single-row toggle.
    """
    content_id = str(entity_id or "").split("::", 1)[0].strip()
    if not content_id:
        return None
    try:
        from database.video_variant_index import get_variant_group_by_content_ids
        indexed = get_variant_group_by_content_ids([content_id]) or {}
    except Exception:
        return None
    group = indexed.get(content_id)
    if not group:
        return None
    members: list[tuple[str, Dict]] = []
    for item in group.get("items") or []:
        cid = str(item.get("content_id") or "").strip()
        if not cid:
            continue
        svc = str(item.get("service_code") or "").strip()
        member_id = f"{cid}::{svc}" if svc else cid
        members.append((
            member_id,
            {
                "content_id": cid,
                "dvd_id": item.get("dvd_id") or "",
                "service_code": svc,
                "variant_group_id": group.get("group_id"),
                "canonical_code": group.get("canonical_code"),
                "variant_group_size": group.get("group_count"),
            },
        ))
    return members or None


@router.post("/toggle")
def toggle_favorite(req: ToggleFavoriteRequest):
    """切换收藏状态。

    video 类型按整个变体组（同一作品的全部版本）一起收藏/取消：点击任何一个
    版本，组内所有版本统一进入/退出收藏，这样无论页面展示哪个版本红心状态
    都一致，收藏页也只出现一张卡。
    """
    if req.entity_type == "video":
        members = _video_group_members(req.entity_id, req.metadata)
        if members:
            member_ids = {member_id for member_id, _ in members}
            if req.entity_id not in member_ids:
                members.append((req.entity_id, dict(req.metadata or {})))
            currently = any(
                favorite.is_favorite("video", member_id) for member_id, _ in members
            )
            target = not currently
            entity_ids = []
            for member_id, member_meta in members:
                meta = dict(member_meta)
                if member_id == req.entity_id and req.metadata:
                    meta.update(req.metadata)
                favorite.set_favorite("video", member_id, meta, favorited=target)
                entity_ids.append(member_id)
            return {
                "is_favorited": target,
                "group_size": len(entity_ids),
                "entity_ids": entity_ids,
            }
    is_favorited = favorite.toggle_favorite(req.entity_type, req.entity_id, req.metadata)
    return {"is_favorited": is_favorited}

@router.get("/status")
def get_favorite_status(entity_type: str, entity_id: str):
    """检查特定实体的收藏状态"""
    return {"is_favorited": favorite.is_favorite(entity_type, entity_id)}

@router.get("/collections", response_model=List[CollectionItem])
def get_collections():
    """获取收藏夹列表"""
    return favorite.list_collections()


@router.post("/collections", response_model=CollectionItem)
def create_collection(req: CollectionRequest):
    """创建收藏夹"""
    try:
        return favorite.create_collection(req.name, req.description)
    except favorite.CollectionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except favorite.CollectionNameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/collections/{collection_id}", response_model=CollectionItem)
def update_collection(collection_id: int, req: CollectionRequest):
    """更新收藏夹"""
    try:
        return favorite.update_collection(collection_id, req.name, req.description)
    except favorite.CollectionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except favorite.CollectionNameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except favorite.CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: int):
    """删除收藏夹"""
    if not favorite.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"deleted": True}
