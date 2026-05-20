from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam
from typing import Any, Optional, Dict
from modules.info_client import get_info_client
from services import cache
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])
_LIST_CACHE_NAMESPACE = "videos"
_LIST_CACHE_TTL = 600
_SEARCH_CACHE_NAMESPACE = "video_search"
_SEARCH_CACHE_TTL = 600
_RANDOM_CACHE_NAMESPACE = "video_random"
_RANDOM_CACHE_TTL = 5
_DETAIL_CACHE_NAMESPACE = "video_detail"
_DETAIL_CACHE_TTL = 600


def _content_cache_id(content_id: str) -> str:
    return content_id.replace("-", "").lower()

async def _apply_translation_to_video(data: dict, *, allow_network: bool = True) -> dict:
    """对单条影片数据应用翻译"""
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return await get_translator_service().translate_video(content_id, data, allow_network=allow_network)


async def _apply_translation_to_videos(items: list[dict], *, allow_network: bool = False) -> list[dict]:
    return await get_translator_service().translate_videos(items, allow_network=allow_network)

@router.get("/search")
async def search_videos(
    q: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    dvd_id: Optional[str] = Query(None),
    maker_id: Optional[int] = Query(None),
    maker_name: Optional[str] = Query(None),
    series_id: Optional[int] = Query(None),
    series_name: Optional[str] = Query(None),
    actress_id: Optional[int] = Query(None),
    actress_name: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    category_name: Optional[str] = Query(None),
    label_id: Optional[int] = Query(None),
    label_name: Optional[str] = Query(None),
    site_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None, description="发行年份"),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    runtime_min: Optional[int] = Query(None),
    runtime_max: Optional[int] = Query(None),
    release_date_from: Optional[str] = Query(None),
    release_date_to: Optional[str] = Query(None),
    service_code: Optional[str] = Query(None, description="影片类型：digital/mono/rental/ebook"),
    sort_by: Optional[str] = Query(None, description="排序字段，如 release_date"),
    sort_order: Optional[str] = Query(None, description="asc 或 desc"),
    random: Optional[str] = Query(None, description="随机排序"),
    include_total: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    _include_total = None if isinstance(include_total, QueryParam) else include_total
    cache_params = {
        "q": q,
        "content_id": content_id,
        "dvd_id": dvd_id,
        "maker_id": maker_id,
        "maker_name": maker_name,
        "series_id": series_id,
        "series_name": series_name,
        "actress_id": actress_id,
        "actress_name": actress_name,
        "category_id": category_id,
        "category_name": category_name,
        "label_id": label_id,
        "label_name": label_name,
        "site_id": site_id,
        "year": year,
        "year_from": year_from,
        "year_to": year_to,
        "runtime_min": runtime_min,
        "runtime_max": runtime_max,
        "release_date_from": release_date_from,
        "release_date_to": release_date_to,
        "service_code": service_code,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "include_total": _include_total,
        "page": page,
        "page_size": page_size,
    }

    async def produce():
        client = get_info_client()
        result = await client.search_videos(
            q=q, content_id=content_id, dvd_id=dvd_id,
            maker_id=maker_id, maker_name=maker_name,
            series_id=series_id, series_name=series_name,
            actress_id=actress_id, actress_name=actress_name,
            category_id=category_id, category_name=category_name,
            label_id=label_id, label_name=label_name,
            site_id=site_id,
            year=year, year_from=year_from, year_to=year_to,
            runtime_min=runtime_min, runtime_max=runtime_max,
            release_date_from=release_date_from, release_date_to=release_date_to,
            service_code=service_code,
            sort_by=sort_by, sort_order=sort_order,
            random=random,
            include_total=_include_total,
            page=page, page_size=page_size
        )
        if result.get("data"):
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
        return result

    if random:
        if _include_total is False:
            random_cache_params = dict(cache_params)
            random_cache_params["random"] = random
            return await cache.get_or_set_response(
                _RANDOM_CACHE_NAMESPACE,
                random_cache_params,
                produce,
                ttl=_RANDOM_CACHE_TTL,
            )
        return await produce()
    return await cache.get_or_set_response(_SEARCH_CACHE_NAMESPACE, cache_params, produce, ttl=_SEARCH_CACHE_TTL)

@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_total: bool = Query(False),
) -> Dict[str, Any]:
    _include_total = False if isinstance(include_total, QueryParam) else bool(include_total)
    cache_params = {"page": page, "page_size": page_size, "include_total": _include_total}

    async def produce():
        client = get_info_client()
        result = await client.list_videos(page=page, page_size=page_size, include_total=_include_total)
        if result.get("data"):
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
        return result

    return await cache.get_or_set_response(_LIST_CACHE_NAMESPACE, cache_params, produce, ttl=_LIST_CACHE_TTL)

@router.get("/{content_id}")
async def get_video(content_id: str, service_code: Optional[str] = Query(None)) -> Dict[str, Any]:
    _service_code = None if isinstance(service_code, QueryParam) else service_code
    cache_params = {
        "content_id": _content_cache_id(content_id),
        "service_code": _service_code,
    }

    async def produce():
        client = get_info_client()
        data = await client.get_video(content_id, service_code=_service_code)
        return await _apply_translation_to_video(data, allow_network=False)

    return await cache.get_or_set_response(
        _DETAIL_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_DETAIL_CACHE_TTL,
    )
