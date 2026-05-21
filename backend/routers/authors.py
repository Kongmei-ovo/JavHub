from fastapi import APIRouter, Query
from typing import Any
from modules.info_client import get_info_client
from services import cache

router = APIRouter(prefix="/api/v1/authors", tags=["authors"])
_CACHE_NAMESPACE = "authors"
_CACHE_TTL = 600


@router.get("")
async def list_authors(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    cache_params = {"q": q, "page": page, "page_size": page_size}

    async def produce():
        client = get_info_client()
        return await client.list_authors(q=q, page=page, page_size=page_size)

    return await cache.get_or_set_response(_CACHE_NAMESPACE, cache_params, produce, ttl=_CACHE_TTL)
