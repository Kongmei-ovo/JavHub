from fastapi import APIRouter, Query
from typing import Any, Optional, Dict
from modules.info_client import get_info_client
from services.translation import apply_translation

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

def _apply_translation_to_video(data: dict) -> dict:
    """对单条影片数据应用翻译"""
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return apply_translation(content_id, data)

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
    year: Optional[int] = Query(None, description="发行年份"),
    sort_by: Optional[str] = Query(None, description="排序字段，如 release_date"),
    sort_order: Optional[str] = Query(None, description="asc 或 desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    client = get_info_client()
    result = await client.search_videos(
        q=q, content_id=content_id, maker_id=maker_id, maker_name=maker_name,
        series_id=series_id, series_name=series_name,
        actress_id=actress_id, actress_name=actress_name,
        category_id=category_id, category_name=category_name,
        year=year,
        sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size
    )
    if result.get("data"):
        result["data"] = [_apply_translation_to_video(item) for item in result["data"]]
    return result

@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    client = get_info_client()
    result = await client.list_videos(page=page, page_size=page_size)
    if result.get("data"):
        result["data"] = [_apply_translation_to_video(item) for item in result["data"]]
    return result

@router.get("/{content_id}")
async def get_video(content_id: str, service_code: Optional[str] = Query(None)) -> Dict[str, Any]:
    client = get_info_client()
    data = await client.get_video(content_id, service_code=service_code)
    return _apply_translation_to_video(data)
