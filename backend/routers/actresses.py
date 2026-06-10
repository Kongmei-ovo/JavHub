from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from fastapi.params import Query as QueryParam
from typing import Any
import math
from modules.info_client import get_info_client
from services import cache
from services.video_variants import enrich_video_variants, filter_movie_items
from services.video_variant_index import apply_indexed_variant_groups
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/actresses", tags=["actresses"])
_LIST_CACHE_NAMESPACE = "actresses"
_LIST_CACHE_TTL = 120
_VIDEOS_CACHE_NAMESPACE = "actress_videos"
_VIDEOS_CACHE_TTL = 600
_GROUPED_VIDEOS_CACHE_NAMESPACE = "actress_videos_grouped_collection"


class BatchActressVideosRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

@router.get("")
async def list_actresses(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    has_valid_avatar: str | None = Query(None),
    cache_control: str | None = Query(None, alias="cache"),
) -> dict[str, Any]:
    _q = None if isinstance(q, QueryParam) else q
    _has_valid_avatar = None if isinstance(has_valid_avatar, QueryParam) else has_valid_avatar
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)
    cache_params = {
        "q": _q,
        "page": page,
        "page_size": page_size,
        "has_valid_avatar": _has_valid_avatar,
    }

    async def produce():
        client = get_info_client()
        if cache_bypass:
            result = await client.list_actresses(
                q=_q,
                page=page,
                page_size=page_size,
                has_valid_avatar=_has_valid_avatar,
                cache_bypass=True,
            )
        else:
            result = await client.list_actresses(
                q=_q,
                page=page,
                page_size=page_size,
                has_valid_avatar=_has_valid_avatar,
            )
        # 为每个 actress 注入翻译字段
        items = result.get("data", []) if isinstance(result, dict) else result
        if isinstance(items, list):
            await get_translator_service().translate_entities(
                items,
                entity_type="actress",
                keys=["name_kanji", "name_romaji", "name_ja", "name_en", "name"],
                allow_network=False,
            )
        return result

    return await cache.get_or_set_response(
        _LIST_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_LIST_CACHE_TTL,
        bypass=cache_bypass,
    )

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
                result["movie_count"] = 0
        await get_translator_service().translate_entities(
            [result],
            entity_type="actress",
            keys=["name_kanji", "name_romaji", "name_ja", "name_en", "name"],
            allow_network=False,
        )
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
    include_total: bool | None = Query(None),
    variant_mode: str = Query("grouped", pattern="^(grouped|flat)$"),
    variant_scope: str = Query("page", pattern="^(page|indexed)$"),
    include_variant_explanations: bool = Query(False),
    cache_control: str | None = Query(None, alias="cache"),
) -> dict[str, Any]:
    # Resolve Query() defaults to plain None for testability
    _inc = None if isinstance(include_supplement, QueryParam) else include_supplement
    _svc = None if isinstance(service_code, QueryParam) else service_code
    _yr  = None if isinstance(year, QueryParam) else year
    _srt = None if isinstance(sort_by, QueryParam) else sort_by
    _include_total = None if isinstance(include_total, QueryParam) else include_total
    _variant_mode = "grouped" if isinstance(variant_mode, QueryParam) else variant_mode
    _variant_scope = "page" if isinstance(variant_scope, QueryParam) else variant_scope
    _include_variant_explanations = False if isinstance(include_variant_explanations, QueryParam) else bool(include_variant_explanations)
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    if _include_total is None and not _inc:
        _include_total = False

    cache_params = {
        "actress_id": actress_id,
        "page": page,
        "page_size": page_size,
        "include_supplement": _inc,
        "service_code": _svc,
        "year": _yr,
        "sort_by": _srt,
        "include_total": _include_total,
        "variant_mode": _variant_mode,
        "variant_scope": _variant_scope,
        "include_variant_explanations": _include_variant_explanations,
    }

    async def produce():
        client = get_info_client()
        cache_bypass = cache.should_bypass_response_cache(_cache_control)
        if _variant_mode == "grouped":
            result = await _get_grouped_actress_videos_collection_with_autopilot(
                client,
                actress_id=actress_id,
                include_supplement=_inc,
                service_code=_svc,
                year=_yr,
                sort_by=_srt,
                include_total=_include_total,
                include_variant_explanations=_include_variant_explanations,
                cache_bypass=cache_bypass,
            )
            total_count = len(result.get("data") or [])
            start = (page - 1) * page_size
            page_items = list(result.get("data") or [])[start:start + page_size]
            if _variant_scope == "indexed" and page_items:
                indexed_items = apply_indexed_variant_groups(
                    page_items,
                    include_explanations=_include_variant_explanations,
                )
                page_items = _prefer_larger_variant_groups(page_items, indexed_items)
            response = dict(result)
            response.update(
                {
                    "data": page_items,
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": _total_pages(total_count, page_size),
                }
            )
            return response

        if cache_bypass:
            result = await client.get_actress_videos(
                actress_id, page=page, page_size=page_size,
                include_supplement=_inc,
                service_code=_svc,
                year=_yr,
                sort_by=_srt,
                include_total=_include_total,
                cache_bypass=True,
            )
        else:
            result = await client.get_actress_videos(
                actress_id, page=page, page_size=page_size,
                include_supplement=_inc,
                service_code=_svc,
                year=_yr,
                sort_by=_srt,
                include_total=_include_total,
            )
        if result.get("data"):
            result["data"] = filter_movie_items(result["data"])
            result["data"] = await _apply_translation_to_videos(result["data"], allow_network=False)
            result["data"] = enrich_video_variants(
                result["data"],
                variant_mode=_variant_mode,
                include_explanations=_include_variant_explanations,
            )
        return result

    return await cache.get_or_set_response(
        _VIDEOS_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_VIDEOS_CACHE_TTL,
        bypass=cache.should_bypass_response_cache(_cache_control),
    )


async def _get_grouped_actress_videos_collection_with_autopilot(
    client: Any,
    *,
    actress_id: int,
    include_supplement: str | None,
    service_code: str | None,
    year: int | None,
    sort_by: str | None,
    include_total: bool | None,
    include_variant_explanations: bool,
    cache_bypass: bool,
) -> dict[str, Any]:
    result = await _get_grouped_actress_videos_collection(
        client,
        actress_id=actress_id,
        include_supplement=include_supplement,
        service_code=service_code,
        year=year,
        sort_by=sort_by,
        include_total=include_total,
        include_variant_explanations=include_variant_explanations,
        cache_bypass=cache_bypass,
    )
    # Resolved view was empty → the supplement pipeline never ran for this
    # actress. Schedule it in the background so the page heals itself.
    if isinstance(result, dict) and result.get("supplement_pending"):
        from services.supplement_autopilot import schedule_actress_supplement
        schedule_actress_supplement(actress_id)
    return result


async def _get_grouped_actress_videos_collection(
    client: Any,
    *,
    actress_id: int,
    include_supplement: str | None,
    service_code: str | None,
    year: int | None,
    sort_by: str | None,
    include_total: bool | None,
    include_variant_explanations: bool,
    cache_bypass: bool,
) -> dict[str, Any]:
    # The full grouped catalog is the same dataset no matter what the caller
    # passed for include_total — that flag only governs whether the outer
    # response exposes a count. Keying the cache on include_total would
    # silently split the catalog into two buckets and let page=2 with
    # include_total=false stop after the upstream API's first page (because
    # the upstream omits total_pages when include_total is false, which makes
    # _get_all_pages think it's done after page 1). Force the inner fetch to
    # always request the total so pagination walks the whole catalog.
    cache_params = {
        "actress_id": actress_id,
        "include_supplement": include_supplement,
        "service_code": service_code,
        "year": year,
        "sort_by": sort_by,
        "include_variant_explanations": include_variant_explanations,
    }

    async def produce() -> dict[str, Any]:
        result = await client.get_all_actress_videos(
            actress_id,
            include_supplement=include_supplement,
            service_code=service_code,
            year=year,
            sort_by=sort_by,
            include_total=True,
            cache_bypass=cache_bypass,
        )
        items = result.get("data", []) if isinstance(result, dict) else []
        if isinstance(items, list):
            items = filter_movie_items(items)
        if isinstance(items, list) and items:
            translated = await _apply_translation_to_videos(items, allow_network=False)
            result = dict(result)
            result["data"] = enrich_video_variants(
                translated,
                variant_mode="grouped",
                include_explanations=include_variant_explanations,
            )
        elif isinstance(result, dict):
            result = dict(result)
            result["data"] = []
        else:
            result = {"data": []}
        return result

    return await cache.get_or_set_response(
        _GROUPED_VIDEOS_CACHE_NAMESPACE,
        cache_params,
        produce,
        ttl=_VIDEOS_CACHE_TTL,
        bypass=cache_bypass,
    )


def _total_pages(total_count: int, page_size: int) -> int:
    if total_count <= 0:
        return 0
    return int(math.ceil(total_count / max(1, page_size)))


def _prefer_larger_variant_groups(
    local_items: list[dict[str, Any]],
    indexed_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(local_items) != len(indexed_items):
        return indexed_items
    result: list[dict[str, Any]] = []
    for local_item, indexed_item in zip(local_items, indexed_items):
        local_count = int(local_item.get("variant_group_count") or 1)
        indexed_count = int(indexed_item.get("variant_group_count") or 1)
        result.append(indexed_item if indexed_count > local_count else local_item)
    return result


@router.post("/batch_videos")
async def batch_get_actress_videos(req: BatchActressVideosRequest) -> dict[str, Any]:
    client = get_info_client()
    ids = req.ids[:20]
    result = await client.batch_get_actress_videos(ids, page=req.page, page_size=req.page_size)
    for info in result.values():
        if isinstance(info, dict) and isinstance(info.get("videos"), list):
            info["videos"] = await _apply_translation_to_videos(info["videos"], allow_network=False)
    return result

async def _apply_translation(data: dict, *, allow_network: bool = True) -> dict:
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return await get_translator_service().translate_video(content_id, data, allow_network=allow_network)


async def _apply_translation_to_videos(items: list[dict], *, allow_network: bool = False) -> list[dict]:
    return await get_translator_service().translate_videos(items, allow_network=allow_network)
