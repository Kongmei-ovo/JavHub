from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam
from typing import Any
from modules.info_client import get_info_client
from services.translation import apply_translation
from database import get_translation
from services.translation import _translate_item

router = APIRouter(prefix="/api/v1/actresses", tags=["actresses"])

@router.get("")
async def list_actresses(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    client = get_info_client()
    result = await client.list_actresses(q=q, page=page, page_size=page_size)
    # 为每个 actress 注入翻译字段
    items = result.get("data", []) if isinstance(result, dict) else result
    if isinstance(items, list):
        for actress in items:
            actress_id = actress.get("id")
            if actress_id:
                trans = get_translation(f"actress:{actress_id}")
                if trans:
                    actress_map = trans.get("actress", {})
                    for name_key in ["name_kanji", "name_romaji", "name_ja", "name_en", "name"]:
                        orig = actress.get(name_key)
                        if orig:
                            actress[f"{name_key}_translated"] = _translate_item(orig, actress_map)
                            break
    return result

@router.get("/{actress_id}")
async def get_actress(actress_id: int) -> dict[str, Any]:
    client = get_info_client()
    result = await client.get_actress(actress_id)
    if isinstance(result, dict):
        # 补充 movie_count（单演员接口不返回此字段，从作品接口获取）
        if "movie_count" not in result:
            try:
                vids = await client.get_actress_videos(actress_id, page=1, page_size=1)
                result["movie_count"] = vids.get("total_count", 0)
            except Exception:
                pass
        trans = get_translation(f"actress:{actress_id}")
        if trans:
            actress_map = trans.get("actress", {})
            for name_key in ["name_kanji", "name_romaji", "name_ja", "name_en", "name"]:
                orig = result.get(name_key)
                if orig:
                    result[f"{name_key}_translated"] = _translate_item(orig, actress_map)
                    break
    return result

@router.get("/{actress_id}/videos")
async def get_actress_videos(
    actress_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_supplement: str | None = Query(None),
    service_code: str | None = Query(None),
    year: int | None = Query(None),
    sort_by: str | None = Query(None),
) -> dict[str, Any]:
    # Resolve Query() defaults to plain None for testability
    _inc = None if isinstance(include_supplement, QueryParam) else include_supplement
    _svc = None if isinstance(service_code, QueryParam) else service_code
    _yr  = None if isinstance(year, QueryParam) else year
    _srt = None if isinstance(sort_by, QueryParam) else sort_by

    client = get_info_client()
    result = await client.get_actress_videos(
        actress_id, page=page, page_size=page_size,
        include_supplement=_inc,
        service_code=_svc,
        year=_yr,
        sort_by=_srt,
    )
    if result.get("data"):
        result["data"] = [_apply_translation(item) for item in result["data"]]
    return result

def _apply_translation(data: dict) -> dict:
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return apply_translation(content_id, data)