from fastapi import APIRouter, Query
from typing import Any, Optional, Dict
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

@router.get("/search")
async def search_videos(
    q: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    maker_id: Optional[int] = Query(None),
    maker_name: Optional[str] = Query(None),
    series_id: Optional[int] = Query(None),
    series_name: Optional[str] = Query(None),
    actress_id: Optional[int] = Query(None),
    actress_name: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    category_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    client = get_info_client()
    return await client.search_videos(
        q=q, content_id=content_id, maker_id=maker_id, maker_name=maker_name,
        series_id=series_id, series_name=series_name,
        actress_id=actress_id, actress_name=actress_name,
        category_id=category_id, category_name=category_name,
        page=page, page_size=page_size
    )

@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    client = get_info_client()
    return await client.list_videos(page=page, page_size=page_size)

@router.get("/{content_id}")
async def get_video(content_id: str, service_code: Optional[str] = Query(None)) -> Dict[str, Any]:
    client = get_info_client()
    return await client.get_video(content_id, service_code=service_code)
