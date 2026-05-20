from fastapi import APIRouter, Query
from modules.info_client import get_info_client
from services import cache
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/series", tags=["series"])
_CACHE_NAMESPACE = "series"
_CACHE_TTL = 600

@router.get("")
async def list_series(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
):
    include_total = False
    cache_params = {"q": q, "page": page, "page_size": page_size, "include_total": include_total}

    async def produce():
        client = get_info_client()
        result = await client.list_series_page(q=q, page=page, page_size=page_size, include_total=include_total)
        page_items = result.get("data", []) if isinstance(result, dict) else []

        # 为当前页注入翻译字段
        await get_translator_service().translate_entities(
            page_items,
            entity_type="series",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )
        return result

    return await cache.get_or_set_response(_CACHE_NAMESPACE, cache_params, produce, ttl=_CACHE_TTL)
