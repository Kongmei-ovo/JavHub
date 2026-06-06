"""Inventory routes kept in the main module plus compatibility facade."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.routing import APIRoute
from pydantic import BaseModel

from database import (
    add_actor_alias, add_exempt_video, add_inventory_job, count_download_candidates, count_snapshot_actors,
    delete_exempt_video, delete_missing_video, download_candidate_stats, download_candidate_summary,
    find_similar_actresses, get_actor_aliases, get_actor_primary_name, get_all_missing_videos,
    get_canonical_actress_id, get_exempt_videos, get_inventory_actor, get_inventory_actors,
    get_inventory_actors_by_ids, get_inventory_job, get_inventory_jobs, get_inventory_videos,
    get_latest_snapshot_key, get_missing_video, get_missing_videos, get_snapshot_actor, get_snapshot_actors,
    get_snapshot_actors_with_inventory_stats, list_actor_mappings_for_actor_ids, list_download_candidates,
    list_download_candidates_page, list_missing_videos_page, mapping_summary_for_snapshot, set_actor_primary_name,
)
from database.base import get_db
from modules.info_client import get_info_client
from routers import inventory_actors as _actors
from routers import inventory_jobs as _jobs
from routers import inventory_mapping as _mapping
from routers.duplicates import _snapshot_duplicates
from services import inventory_extras
from services.cache import get_or_set_response, should_bypass_response_cache


router = APIRouter(prefix="/api/inventory", tags=["inventory"])

TriggerJobRequest, PipelineRequest = _jobs.TriggerJobRequest, _jobs.PipelineRequest
MergeActorsRequest, PrimaryNameRequest = _actors.MergeActorsRequest, _actors.PrimaryNameRequest
ActorMappingRequest, ActorMappingAiReviewRequest = _mapping.ActorMappingRequest, _mapping.ActorMappingAiReviewRequest
_ACTORS_PAYLOAD = _actors._inventory_actors_payload
_MAPPING_UNMAPPED_PAYLOAD = _mapping._unmapped_actor_mappings_payload


def _sync_jobs_module() -> None:
    for name in ("add_inventory_job", "get_inventory_jobs", "get_inventory_job"): setattr(_jobs, name, globals()[name])


def _sync_actor_module() -> None:
    names = (
        "add_actor_alias", "find_similar_actresses", "get_actor_aliases", "get_actor_primary_name",
        "get_canonical_actress_id", "get_inventory_actor", "get_inventory_actors_by_ids", "get_inventory_videos",
        "get_latest_snapshot_key", "get_missing_videos", "get_snapshot_actor", "get_snapshot_actors",
        "get_snapshot_actors_with_inventory_stats", "set_actor_primary_name",
    )
    for name in names: setattr(_actors, name, globals()[name])
    current = globals().get("_inventory_actors_payload")
    _actors._inventory_actors_payload = _ACTORS_PAYLOAD if current is _FACADE_INVENTORY_ACTORS_PAYLOAD else current


def _sync_mapping_module() -> None:
    names = ("get_latest_snapshot_key", "get_snapshot_actors", "list_actor_mappings_for_actor_ids", "mapping_summary_for_snapshot")
    for name in names: setattr(_mapping, name, globals()[name])
    _mapping._emby_image_url = globals()["_emby_image_url"]
    current = globals().get("_unmapped_actor_mappings_payload")
    _mapping._unmapped_actor_mappings_payload = _MAPPING_UNMAPPED_PAYLOAD if current is _FACADE_UNMAPPED_ACTOR_MAPPINGS_PAYLOAD else current


def trigger_job(req: TriggerJobRequest): _sync_jobs_module(); return _jobs.trigger_job(req)
def run_pipeline(req: PipelineRequest): _sync_jobs_module(); return _jobs.run_pipeline(req)
def list_jobs(): _sync_jobs_module(); return _jobs.list_jobs()
def get_job(job_id: int): _sync_jobs_module(); return _jobs.get_job(job_id)
def _emby_image_url(actress_id: str, image_tag: str) -> str: return _actors._emby_image_url(actress_id, image_tag)
def _inventory_actors_payload(*args, **kwargs) -> dict: _sync_actor_module(); return _ACTORS_PAYLOAD(*args, **kwargs)
async def list_actors(*args, **kwargs): _sync_actor_module(); return await _actors.list_actors(*args, **kwargs)
def merge_actors_javhub(req: MergeActorsRequest): _sync_actor_module(); return _actors.merge_actors_javhub(req)
def find_similar_actors(*args, **kwargs): _sync_actor_module(); return _actors.find_similar_actors(*args, **kwargs)
async def get_actor(actress_id: int): _sync_actor_module(); return await _actors.get_actor(actress_id)
async def get_actor_emby_videos(actress_id: int): _sync_actor_module(); return await _actors.get_actor_emby_videos(actress_id)
def set_primary_name(actress_id: int, req: PrimaryNameRequest): _sync_actor_module(); return _actors.set_primary_name(actress_id, req)
def _unmapped_actor_mappings_payload(*args, **kwargs) -> dict: _sync_mapping_module(); return _MAPPING_UNMAPPED_PAYLOAD(*args, **kwargs)
def list_mappings(*args, **kwargs): _sync_mapping_module(); return _mapping.list_mappings(*args, **kwargs)
def actor_mapping_summary(): _sync_mapping_module(); return _mapping.actor_mapping_summary()
def list_unmapped_actor_mappings(*args, **kwargs): _sync_mapping_module(); return _mapping.list_unmapped_actor_mappings(*args, **kwargs)
async def search_mapping_candidates(*args, **kwargs): return await _mapping.search_mapping_candidates(*args, **kwargs)
async def ai_review_mapping(*args, **kwargs): return await _mapping.ai_review_mapping(*args, **kwargs)
async def generate_mapping_candidates(*args, **kwargs): return await _mapping.generate_mapping_candidates(*args, **kwargs)
async def auto_match_mappings(*args, **kwargs): return await _mapping.auto_match_mappings(*args, **kwargs)
def confirm_mapping(*args, **kwargs): return _mapping.confirm_mapping(*args, **kwargs)
def ignore_mapping(*args, **kwargs): return _mapping.ignore_mapping(*args, **kwargs)
def delete_mapping(*args, **kwargs): return _mapping.delete_mapping(*args, **kwargs)
_FACADE_INVENTORY_ACTORS_PAYLOAD = _inventory_actors_payload
_FACADE_UNMAPPED_ACTOR_MAPPINGS_PAYLOAD = _unmapped_actor_mappings_payload


@router.get("/snapshots/latest")
def get_latest_snapshot(include_actors: bool = False):
    """Return latest inventory snapshot metadata."""
    key = get_latest_snapshot_key()
    if not key:
        return {
            "snapshot_key": None,
            "actor_count": 0,
            "actors": {"data": [], "total": 0, "deferred": True},
        }
    actor_count = count_snapshot_actors(key)
    if include_actors:
        return {"snapshot_key": key, "actor_count": actor_count, "actors": get_snapshot_actors(key)}
    return {
        "snapshot_key": key,
        "actor_count": actor_count,
        "actors": {"data": [], "total": actor_count, "deferred": True},
    }


@router.get("/overview")
async def library_organize_overview(
    actor_search: Optional[str] = None,
    actor_sort: str = "missing_count",
    mapping_search: Optional[str] = None,
    candidate_status: Optional[str] = "candidate",
    candidate_search: Optional[str] = None,
    candidate_needs_magnet: Optional[bool] = None,
    cache_control: Optional[str] = Query(None, alias="cache"),
) -> dict:
    """Return the first-screen inventory organization payload."""
    params = {
        "actor_search": actor_search,
        "actor_sort": actor_sort,
        "mapping_search": mapping_search,
        "candidate_status": candidate_status,
        "candidate_search": candidate_search,
        "candidate_needs_magnet": candidate_needs_magnet,
    }

    async def produce() -> dict:
        return await asyncio.to_thread(
            _library_organize_overview_payload,
            actor_search=actor_search,
            actor_sort=actor_sort,
            mapping_search=mapping_search,
            candidate_status=candidate_status,
            candidate_search=candidate_search,
            candidate_needs_magnet=candidate_needs_magnet,
        )

    return await get_or_set_response(
        "inventory_overview",
        params,
        produce,
        ttl=10,
        bypass=should_bypass_response_cache(cache_control),
    )


def _library_organize_overview_payload(
    actor_search: Optional[str] = None,
    actor_sort: str = "missing_count",
    mapping_search: Optional[str] = None,
    candidate_status: Optional[str] = "candidate",
    candidate_search: Optional[str] = None,
    candidate_needs_magnet: Optional[bool] = None,
) -> dict:
    snapshot_key = get_latest_snapshot_key()
    snapshot_actor_count = count_snapshot_actors(snapshot_key)
    candidate_size = 80
    candidate_page = list_download_candidates_page(
        status=candidate_status,
        actress_id=None,
        source="inventory",
        q=candidate_search,
        needs_magnet=candidate_needs_magnet,
        limit=candidate_size,
        offset=0,
        include_stats=False,
    )
    candidate_total = int(candidate_page["total"] or 0)
    candidate_stats = download_candidate_summary(status="candidate", source="inventory")
    missing_page_size = 80
    missing_page = list_missing_videos_page(limit=missing_page_size, offset=0)
    missing_total = int(missing_page.get("total") or 0)
    missing_limit = int(missing_page.get("limit") or missing_page_size)
    return {
        "snapshot": {"snapshot_key": snapshot_key, "actor_count": snapshot_actor_count},
        "actors": _inventory_actors_payload(snapshot_key, search=actor_search, actor_sort=actor_sort, page=1, page_size=60),
        "mapping": {
            "summary": mapping_summary_for_snapshot(snapshot_key),
            "unmapped": _unmapped_actor_mappings_payload(search=mapping_search, limit=80, snapshot_key=snapshot_key),
        },
        "missing": {
            "data": missing_page["data"],
            "total": missing_total,
            "page": 1,
            "page_size": missing_limit,
            "total_pages": max(1, (missing_total + missing_limit - 1) // missing_limit),
        },
        "candidates": {
            "data": candidate_page["data"],
            "total": candidate_total,
            "page": 1,
            "page_size": candidate_size,
            "total_pages": max(1, (candidate_total + candidate_size - 1) // candidate_size),
            "stats": candidate_stats,
        },
        "duplicates": {"data": [], "total": 0, "deferred": True},
        "jobs": {"data": get_inventory_jobs(limit=50)},
    }


async def list_extras(
    actor_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=1000),
    cache_control: Optional[str] = Query(None, alias="cache"),
) -> dict:
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0}

    safe_limit = max(1, min(int(limit or 200), 1000))
    params = {"snapshot_key": snapshot_key, "actor_id": actor_id, "limit": safe_limit}

    async def produce() -> dict:
        rows = await inventory_extras.list_extras(snapshot_key, actor_id=actor_id, limit=safe_limit)
        return {"data": rows, "total": len(rows)}

    return await get_or_set_response(
        "inventory_extras",
        params,
        produce,
        ttl=30,
        bypass=should_bypass_response_cache(cache_control),
    )


router.routes.append(APIRoute("/api/v1/inventory/extras", list_extras, methods=["GET"]))


@router.get("/missing")
def list_missing(page: int = 1, page_size: int = 80):
    """Return paged missing videos."""
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(int(page_size or 80), 500))
    offset = (safe_page - 1) * safe_page_size
    result = list_missing_videos_page(limit=safe_page_size, offset=offset)
    total = int(result.get("total") or 0)
    limit = int(result.get("limit") or safe_page_size)
    return {
        "data": result["data"],
        "total": total,
        "page": safe_page,
        "page_size": limit,
        "total_pages": max(1, (total + limit - 1) // limit),
    }


@router.get("/missing/{actress_id}")
def list_missing_by_actor(actress_id: int):
    """Return missing videos for one actor."""
    return {"data": get_missing_videos(actress_id)}


@router.delete("/missing/{content_id}")
def remove_missing(content_id: str):
    delete_missing_video(content_id)
    return {"success": True}


@router.get("/exempt")
def list_exempt():
    return {"data": get_exempt_videos()}


class ExemptRequest(BaseModel):
    content_id: str
    actress_id: int
    reason: str = ""


@router.post("/exempt")
def exempt_video(req: ExemptRequest):
    add_exempt_video(req.content_id, req.actress_id, req.reason, "manual")
    delete_missing_video(req.content_id)
    return {"success": True}


@router.delete("/exempt/{content_id}")
def unexempt_video(content_id: str):
    delete_exempt_video(content_id)
    return {"success": True}


@router.get("/aliases")
def list_aliases():
    return {"data": get_actor_aliases()}


class AliasRequest(BaseModel):
    alias_id: int
    canonical_id: int


@router.post("/aliases")
def add_alias(req: AliasRequest):
    add_actor_alias(req.alias_id, req.canonical_id)
    return {"success": True}


@router.delete("/aliases/{alias_id}")
def delete_alias(alias_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actor_aliases WHERE id = ?", (alias_id,))
    return {"success": True}


def _find_missing_video(content_id: str) -> Optional[dict]:
    return get_missing_video(content_id)


def _candidate_payload(video: dict, content_id: str, missing_video: dict, reason: str) -> dict:
    return {
        "content_id": video.get("content_id") or video.get("dvd_id") or content_id,
        "dvd_id": video.get("dvd_id") or content_id,
        "title": video.get("title_ja") or video.get("title_en") or video.get("title") or missing_video.get("title") or "",
        "actress_id": missing_video.get("actress_id"),
        "actress_name": None,
        "jacket_thumb_url": video.get("jacket_thumb_url") or video.get("jacket_full_url") or missing_video.get("jacket_thumb_url"),
        "release_date": video.get("release_date") or missing_video.get("release_date"),
        "source": "inventory",
        "reason": reason,
    }


def _fallback_candidate_payload(content_id: str, missing_video: dict, reason: str) -> dict:
    return {
        "content_id": content_id,
        "dvd_id": content_id,
        "title": missing_video.get("title") or content_id,
        "actress_id": missing_video.get("actress_id"),
        "jacket_thumb_url": missing_video.get("jacket_thumb_url"),
        "release_date": missing_video.get("release_date"),
        "source": "inventory",
        "reason": reason,
    }


@router.post("/fill/{content_id}")
async def fill_video(content_id: str):
    """Convert one missing video to a download candidate."""
    from database import upsert_download_candidate

    missing_video = _find_missing_video(content_id) or {}
    info = get_info_client()
    try:
        video = await info.get_video(content_id)
        candidate = upsert_download_candidate(**_candidate_payload(video, content_id, missing_video, "inventory_fill"))
    except Exception:
        candidate = upsert_download_candidate(**_fallback_candidate_payload(content_id, missing_video, "inventory_fill_fallback"))
    return {"success": True, "candidate": candidate}


@router.post("/fill-all")
async def fill_all_videos(limit: int = 100, offset: int = 0, sample_limit: int = 20):
    """Convert a page of missing videos to download candidates."""
    from database import upsert_download_candidate

    safe_limit = max(1, min(int(limit or 100), 100))
    safe_offset = max(0, int(offset or 0))
    page = list_missing_videos_page(limit=safe_limit, offset=safe_offset)
    info = get_info_client()
    count = 0
    candidates = []
    safe_sample_limit = max(0, min(int(sample_limit or 0), 100))
    for video_row in page["data"]:
        content_id = video_row["content_id"]
        try:
            video = await info.get_video(content_id)
            candidate = upsert_download_candidate(**_candidate_payload(video, content_id, video_row, "inventory_fill_all"))
        except Exception:
            candidate = upsert_download_candidate(**_fallback_candidate_payload(content_id, video_row, "inventory_fill_all_fallback"))
        if len(candidates) < safe_sample_limit:
            candidates.append(candidate)
        count += 1
    total = int(page.get("total") or 0)
    page_limit = int(page.get("limit") or safe_limit)
    page_offset = int(page.get("offset") or safe_offset)
    return {
        "success": True, "count": count, "total": total, "limit": page_limit, "offset": page_offset,
        "has_more": page_offset + count < total, "sample_count": len(candidates), "truncated": count > len(candidates),
        "candidates": candidates,
    }
