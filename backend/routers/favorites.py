import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import favorite
from modules.info_client import get_info_client
from services import cache as response_cache
from services.cache import should_bypass_response_cache
from services.video_variant_index import apply_indexed_variant_groups
from services.video_variants import enrich_video_variants
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/favorites", tags=["Favorites"])

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


def _query_default(value, fallback=None):
    if hasattr(value, "default"):
        return fallback if value.default is None else value.default
    return value


@router.get("")
async def get_favorites(
    entity_type: Optional[str] = Query(None),
    include_metadata: bool = Query(False),
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """获取收藏列表；默认只返回全局状态需要的轻量索引。"""
    entity_type_value = _query_default(entity_type)
    include_metadata_value = bool(_query_default(include_metadata, False))
    cache_control_value = _query_default(cache_control)
    bypass_cache = should_bypass_response_cache(cache_control_value)
    cache_params = {
        "generation": await response_cache.get_data_generation_async("favorites"),
        "entity_type": entity_type_value,
        "include_metadata": include_metadata_value,
    }

    async def produce():
        loader = favorite.list_favorites if include_metadata_value else favorite.list_favorite_index
        return await asyncio.to_thread(loader, entity_type_value)

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
    limit: int = Query(48),
    offset: int = Query(0),
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """分页获取 video 收藏详情，避免收藏页一次 fanout 所有 JavInfo 请求。"""
    limit_value = max(1, min(int(_query_default(limit, 48) or 48), 200))
    offset_value = max(0, int(_query_default(offset, 0) or 0))
    cache_control_value = _query_default(cache_control)
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
    results = enrich_video_variants(results, variant_mode="flat", include_explanations=True)
    results = apply_indexed_variant_groups(results, include_explanations=True)
    return results

@router.post("/toggle")
def toggle_favorite(req: ToggleFavoriteRequest):
    """切换收藏状态"""
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
