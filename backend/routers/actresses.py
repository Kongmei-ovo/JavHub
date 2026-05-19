from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from fastapi.params import Query as QueryParam
from typing import Any
from modules.info_client import get_info_client
from services import cache
from translations import get_translator_service

router = APIRouter(prefix="/api/v1/actresses", tags=["actresses"])
_LIST_CACHE_NAMESPACE = "actresses"
_LIST_CACHE_TTL = 120


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
) -> dict[str, Any]:
    _q = None if isinstance(q, QueryParam) else q
    _has_valid_avatar = None if isinstance(has_valid_avatar, QueryParam) else has_valid_avatar
    cache_params = {
        "q": _q,
        "page": page,
        "page_size": page_size,
        "has_valid_avatar": _has_valid_avatar,
    }

    async def produce():
        client = get_info_client()
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

    return await cache.get_or_set_response(_LIST_CACHE_NAMESPACE, cache_params, produce, ttl=_LIST_CACHE_TTL)

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
        result["data"] = [await _apply_translation(item, allow_network=False) for item in result["data"]]
    return result


@router.post("/batch_videos")
async def batch_get_actress_videos(req: BatchActressVideosRequest) -> dict[str, Any]:
    client = get_info_client()
    ids = req.ids[:20]
    result = await client.batch_get_actress_videos(ids, page=req.page, page_size=req.page_size)
    for info in result.values():
        if isinstance(info, dict) and isinstance(info.get("videos"), list):
            info["videos"] = [await _apply_translation(item, allow_network=False) for item in info["videos"]]
    return result

async def _apply_translation(data: dict, *, allow_network: bool = True) -> dict:
    content_id = data.get("content_id") or data.get("dvd_id", "").replace("-", "").replace("_", "").lower()
    if not content_id:
        return data
    return await get_translator_service().translate_video(content_id, data, allow_network=allow_network)
