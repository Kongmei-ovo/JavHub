from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam
from typing import Any, Optional, Dict
import re
from modules.info_client import get_info_client
from services import cache
from services.video_variants import enrich_video_variants
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


_CANONICAL_CODE_RE = re.compile(r"^([A-Z]+)-?([0-9]+)$")


def _exact_code_variant_candidates(code: str | None) -> list[str]:
    raw = str(code or "").strip().upper()
    match = _CANONICAL_CODE_RE.match(raw)
    if not match:
        return []
    prefix, digits = match.groups()
    if len(prefix) < 3:
        return []
    number = str(int(digits))
    padded = number.zfill(max(5, len(digits)))
    dashed = f"{prefix}-{number}"
    return [
        f"TK{dashed}",
        f"{dashed}BOD",
        f"{dashed}DOD",
        f"{dashed}RDOD",
        f"4{prefix}{number}",
        f"{prefix}{padded}",
    ]


async def _expand_exact_code_variants(
    client: Any,
    result: dict[str, Any],
    *,
    content_id: str | None,
    dvd_id: str | None,
    cache_bypass: bool,
) -> dict[str, Any]:
    items = result.get("data")
    if not isinstance(items, list) or len(items) != 1:
        return result
    search_code = content_id or dvd_id
    candidates = _exact_code_variant_candidates(search_code)
    if not candidates:
        return result

    seen = {str(items[0].get("content_id") or items[0].get("dvd_id") or "").lower()}
    expanded = list(items)
    for candidate in candidates:
        if candidate.upper() == str(search_code or "").upper():
            continue
        try:
            extra = await client.search_videos(
                content_id=candidate,
                page=1,
                page_size=5,
                include_total=False,
                cache_bypass=cache_bypass,
            )
        except Exception:
            continue
        for item in extra.get("data") or []:
            key = str(item.get("content_id") or item.get("dvd_id") or "").lower()
            if not key or key in seen:
                continue
            seen.add(key)
            expanded.append(item)
    if len(expanded) > len(items):
        result = dict(result)
        result["data"] = expanded
    return result

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
    variant_mode: str = Query("grouped", pattern="^(grouped|flat)$"),
    include_variant_explanations: bool = Query(False),
    cache_control: str | None = Query(None, alias="cache"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    _include_total = None if isinstance(include_total, QueryParam) else include_total
    _variant_mode = "grouped" if isinstance(variant_mode, QueryParam) else variant_mode
    _include_variant_explanations = False if isinstance(include_variant_explanations, QueryParam) else bool(include_variant_explanations)
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
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
        "variant_mode": _variant_mode,
        "include_variant_explanations": _include_variant_explanations,
        "page": page,
        "page_size": page_size,
    }

    async def produce():
        client = get_info_client()
        if cache_bypass:
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
                page=page, page_size=page_size,
                cache_bypass=True,
            )
        else:
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
                page=page, page_size=page_size,
            )
        if result.get("data"):
            if _variant_mode == "grouped" and (content_id or dvd_id):
                result = await _expand_exact_code_variants(
                    client,
                    result,
                    content_id=content_id,
                    dvd_id=dvd_id,
                    cache_bypass=cache_bypass,
                )
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
            result["data"] = enrich_video_variants(
                result["data"],
                variant_mode=_variant_mode,
                include_explanations=_include_variant_explanations,
            )
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
                bypass=cache_bypass,
            )
        return await produce()
    return await cache.get_or_set_response(
        _SEARCH_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_SEARCH_CACHE_TTL,
        bypass=cache_bypass,
    )

@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_total: bool = Query(False),
    cache_control: str | None = Query(None, alias="cache"),
) -> Dict[str, Any]:
    _include_total = False if isinstance(include_total, QueryParam) else bool(include_total)
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    cache_params = {"page": page, "page_size": page_size, "include_total": _include_total}

    async def produce():
        client = get_info_client()
        if cache_bypass:
            result = await client.list_videos(
                page=page,
                page_size=page_size,
                include_total=_include_total,
                cache_bypass=True,
            )
        else:
            result = await client.list_videos(page=page, page_size=page_size, include_total=_include_total)
        if result.get("data"):
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
        return result

    return await cache.get_or_set_response(
        _LIST_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_LIST_CACHE_TTL,
        bypass=cache_bypass,
    )

@router.get("/{content_id}")
async def get_video(
    content_id: str,
    service_code: Optional[str] = Query(None),
    cache_control: str | None = Query(None, alias="cache"),
) -> Dict[str, Any]:
    _service_code = None if isinstance(service_code, QueryParam) else service_code
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    cache_params = {
        "content_id": _content_cache_id(content_id),
        "service_code": _service_code,
    }

    async def produce():
        client = get_info_client()
        if cache_bypass:
            data = await client.get_video(content_id, service_code=_service_code, cache_bypass=True)
        else:
            data = await client.get_video(content_id, service_code=_service_code)
        return await _apply_translation_to_video(data, allow_network=False)

    return await cache.get_or_set_response(
        _DETAIL_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_DETAIL_CACHE_TTL,
        bypass=cache_bypass,
    )
