from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam
from modules.info_client import get_info_client
from services import cache
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/labels", tags=["labels"])
_CACHE_NAMESPACE = "labels"
_CACHE_TTL = 600


@router.get("")
async def list_labels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    cache_control: str | None = Query(None, alias="cache"),
):
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    include_total = True
    cache_params = {"q": q, "page": page, "page_size": page_size, "include_total": include_total}

    async def produce():
        client = get_info_client()
        if cache_bypass:
            result = await client.list_labels_page(
                q=q,
                page=page,
                page_size=page_size,
                include_total=include_total,
                cache_bypass=True,
            )
        else:
            result = await client.list_labels_page(q=q, page=page, page_size=page_size, include_total=include_total)
        if isinstance(result, dict):
            page_items = result.get("data", []) if isinstance(result.get("data"), list) else []
        else:
            items = result if isinstance(result, list) else []
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = items[start:end]
            result = {
                "data": page_items,
                "page": page,
                "page_size": page_size,
                "total_count": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            }

        await get_translator_service().translate_entities(
            page_items,
            entity_type="label",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )
        return result

    return await cache.get_or_set_response(
        _CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_CACHE_TTL,
        bypass=cache_bypass,
    )
