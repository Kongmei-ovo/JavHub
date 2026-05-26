import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import favorite
from modules.info_client import get_info_client
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

@router.get("")
async def get_favorites(entity_type: Optional[str] = Query(None)):
    """获取收藏列表（轻量，仅 ID + 元数据）"""
    return favorite.list_favorites(entity_type)


@router.get("/videos")
async def get_favorite_videos():
    """获取 video 类型收藏的完整影片数据（JavInfoApi + 翻译）"""
    items = favorite.list_favorites("video")
    if not items:
        return []

    client = get_info_client()

    async def fetch_one(item):
        metadata = item.get("metadata") or {}
        content_id = metadata.get("content_id") or metadata.get("dvd_id") or str(item["entity_id"]).split("::", 1)[0]
        service_code = metadata.get("service_code") or None
        try:
            data = await client.get_video(content_id, service_code=service_code)
            data = await get_translator_service().translate_video(content_id, data, allow_network=False)
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
async def toggle_favorite(req: ToggleFavoriteRequest):
    """切换收藏状态"""
    is_favorited = favorite.toggle_favorite(req.entity_type, req.entity_id, req.metadata)
    return {"is_favorited": is_favorited}

@router.get("/status")
async def get_favorite_status(entity_type: str, entity_id: str):
    """检查特定实体的收藏状态"""
    return {"is_favorited": favorite.is_favorite(entity_type, entity_id)}

@router.get("/collections", response_model=List[CollectionItem])
async def get_collections():
    """获取收藏夹列表"""
    return favorite.list_collections()


@router.post("/collections", response_model=CollectionItem)
async def create_collection(req: CollectionRequest):
    """创建收藏夹"""
    try:
        return favorite.create_collection(req.name, req.description)
    except favorite.CollectionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except favorite.CollectionNameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/collections/{collection_id}", response_model=CollectionItem)
async def update_collection(collection_id: int, req: CollectionRequest):
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
async def delete_collection(collection_id: int):
    """删除收藏夹"""
    if not favorite.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"deleted": True}
