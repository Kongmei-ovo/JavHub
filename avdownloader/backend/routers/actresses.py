from fastapi import APIRouter, Query
from typing import Any
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/actresses", tags=["actresses"])

@router.get("")
async def list_actresses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    client = get_info_client()
    return await client.list_actresses(page=page, page_size=page_size)

@router.get("/{actress_id}")
async def get_actress(actress_id: int) -> dict[str, Any]:
    client = get_info_client()
    return await client.get_actress(actress_id)

@router.get("/{actress_id}/videos")
async def get_actress_videos(
    actress_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    client = get_info_client()
    return await client.get_actress_videos(actress_id, page=page, page_size=page_size)