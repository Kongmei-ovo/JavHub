from fastapi import APIRouter
from modules.info_client import get_info_client
from database import get_translation
from services.translation import _translate_item

router = APIRouter(prefix="/api/v1/series", tags=["series"])

@router.get("")
async def list_series():
    client = get_info_client()
    series_list = await client.list_series()
    # 为每个 series 注入翻译字段
    items = series_list if isinstance(series_list, list) else (series_list.get("data", []) if isinstance(series_list, dict) else [])
    if isinstance(items, list):
        for series in items:
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
    return series_list