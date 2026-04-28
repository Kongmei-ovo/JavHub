from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import favorite

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

@router.get("/", response_model=List[FavoriteItem])
async def get_favorites(entity_type: Optional[str] = Query(None)):
    """获取收藏列表"""
    return favorite.list_favorites(entity_type)

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
