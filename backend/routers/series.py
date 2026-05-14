from fastapi import APIRouter, Query
from modules.info_client import get_info_client
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/series", tags=["series"])

@router.get("")
async def list_series(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
):
    client = get_info_client()
    series_list = await client.list_series(q=q)
    # series_list 是完整列表（缓存），在此做分页
    items = series_list if isinstance(series_list, list) else []
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    # 为当前页注入翻译字段
    await get_translator_service().translate_entities(
        page_items,
        entity_type="series",
        keys=["name_ja", "name_en", "name"],
    )

    return {
        "data": page_items,
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
