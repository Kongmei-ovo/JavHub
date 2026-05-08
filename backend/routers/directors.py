from fastapi import APIRouter, Query
from typing import Any
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/v1/directors", tags=["directors"])


@router.get("")
async def list_directors(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    client = get_info_client()
    return await client.list_directors(q=q, page=page, page_size=page_size)
