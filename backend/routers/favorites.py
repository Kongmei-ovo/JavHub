import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import favorite
from modules.info_client import get_info_client
from services.translation import apply_translation

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

@router.get("")
async def get_favorites(entity_type: Optional[str] = Query(None)):
    """获取收藏列表（轻量，仅 ID + 元数据）"""
    return favorite.list_favorites(entity_type)


@router.get("/videos")
async def get_favorite_videos():
    """获取 video 类型收藏的完整影片数据（javinfo + metatube + 翻译）"""
    items = favorite.list_favorites("video")
    if not items:
        return []

    client = get_info_client()

    async def fetch_one(item):
        # entity_id 就是 content_id，JavInfoApi 通用键
        content_id = item["entity_id"]
        try:
            data = await client.get_video(content_id)
            data = apply_translation(content_id, data)
            data["_created_at"] = item["created_at"]
            return data
        except Exception as e:
            return {
                "content_id": content_id,
                "dvd_id": content_id,
                "title_ja": content_id,
                "_created_at": item["created_at"],
                "_error": str(e),
            }

    results = await asyncio.gather(*[fetch_one(item) for item in items])
    results.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
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
