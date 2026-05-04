from fastapi import APIRouter, Query
from modules.info_client import get_info_client
from database import get_translation
from services.translation import _translate_item

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
    for series in page_items:
        series_id = series.get("id")
        if series_id:
            trans = get_translation(f"series:{series_id}")
            if trans:
                series_map = trans.get("series", {})
                for name_key in ["name_ja", "name_en", "name"]:
                    orig = series.get(name_key)
                    if orig:
                        series[f"{name_key}_translated"] = _translate_item(orig, series_map)
                        break

    return {
        "data": page_items,
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }