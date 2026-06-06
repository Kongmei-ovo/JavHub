"""Inventory actor mapping routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import (
    get_latest_snapshot_key,
    get_snapshot_actors,
    list_actor_mappings_for_actor_ids,
    mapping_summary_for_snapshot,
)
from routers.inventory_actors import _emby_image_url


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class ActorMappingRequest(BaseModel):
    emby_actor_id: str | int
    emby_actor_name: str
    javinfo_actress_id: Optional[int] = None
    javinfo_actress_name: Optional[str] = None
    confidence: float = 1.0
    source: str = "manual"
    javinfo_avatar_url: Optional[str] = None
    movie_count: Optional[int] = None
    confidence_breakdown: Optional[dict] = None
    confidence_label: Optional[str] = None
    risk_flags: Optional[list[str]] = None


class ActorMappingAiReviewRequest(ActorMappingRequest):
    pass


def _unmapped_actor_mappings_payload(
    search: str | None = None,
    limit: int = 80,
    snapshot_key: str | None = None,
) -> dict:
    from services.actor_mapping_candidates import mapping_candidate_from_row

    key = snapshot_key if snapshot_key is not None else get_latest_snapshot_key()
    if not key:
        return {"data": [], "total": 0, "snapshot_key": None}
    data = []
    page = 1
    page_size = 80
    while len(data) < limit:
        actors_page = get_snapshot_actors(key, search=search, page=page, page_size=page_size)
        actors = actors_page.get("data", [])
        if not actors:
            break
        actor_ids = [str(actor.get("actress_id") or "") for actor in actors]
        mapping_rows = list_actor_mappings_for_actor_ids(actor_ids)
        candidates_by_actor = {}
        for row in mapping_rows:
            if row.get("status") != "candidate":
                continue
            actor_key = str(row.get("emby_actor_id") or "")
            if not actor_key:
                continue
            candidates_by_actor.setdefault(actor_key, []).append(mapping_candidate_from_row(row))
        decisions = {
            str(row["emby_actor_id"]): row
            for row in mapping_rows
            if row.get("status") in ("confirmed", "ignored") and row.get("javinfo_actress_id") is None
        }
        confirmed_actor_ids = {
            str(row["emby_actor_id"])
            for row in mapping_rows
            if row.get("status") == "confirmed"
        }
        for actor in actors:
            actor_id = str(actor.get("actress_id"))
            if actor_id in decisions or actor_id in confirmed_actor_ids:
                continue
            image_tag = actor.get("image_tag", "")
            candidates = candidates_by_actor.get(actor_id, [])
            data.append({
                "emby_actor_id": actor_id,
                "emby_actor_name": actor.get("actress_name", ""),
                "total_videos": actor.get("total_videos", 0),
                "avatar_url": _emby_image_url(actor_id, image_tag),
                "candidates": candidates,
                "candidate_count": len(candidates),
            })
            if len(data) >= limit:
                break
        if page >= int(actors_page.get("total_pages") or page):
            break
        page += 1
    return {"data": data, "total": len(data), "snapshot_key": key}


@router.get("/actor-mappings")
def list_mappings(
    status: Optional[str] = None,
    q: Optional[str] = None,
    emby_actor_id: Optional[str] = None,
    limit: int = 200,
):
    """List Emby actor -> JavInfo actress mappings."""
    from database import list_actor_mappings

    return {"data": list_actor_mappings(status=status, q=q, emby_actor_id=emby_actor_id, limit=limit)}


@router.get("/actor-mappings/summary")
def actor_mapping_summary():
    """Return actor mapping coverage for the latest Emby snapshot."""
    snapshot_key = get_latest_snapshot_key()
    return {"snapshot_key": snapshot_key, **mapping_summary_for_snapshot(snapshot_key)}


@router.get("/actor-mappings/unmapped")
def list_unmapped_actor_mappings(search: Optional[str] = None, limit: int = 200):
    """List latest-snapshot actors that are not confirmed or ignored."""
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0, "snapshot_key": None}
    return _unmapped_actor_mappings_payload(search=search, limit=max(1, min(limit, 500)), snapshot_key=snapshot_key)


@router.get("/actor-mappings/search")
async def search_mapping_candidates(
    emby_actor_id: str,
    emby_actor_name: str,
    q: Optional[str] = None,
    limit: int = 10,
):
    """Search JavInfo actresses for an actor-mapping candidate."""
    from services.actor_mapping_candidates import search_actor_mapping_candidates

    try:
        return await search_actor_mapping_candidates(
            emby_actor_id=emby_actor_id,
            emby_actor_name=emby_actor_name,
            q=q,
            limit=max(1, min(limit, 30)),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"JavInfo 演员查找失败: {exc}") from exc


@router.post("/actor-mappings/ai-review")
async def ai_review_mapping(req: ActorMappingAiReviewRequest):
    """Ask the configured AI provider to review one candidate mapping."""
    if not req.javinfo_actress_id:
        raise HTTPException(status_code=400, detail="javinfo_actress_id is required")
    from database import upsert_actor_mapping
    from services.actor_mapping_candidates import review_actor_mapping_with_ai

    mapping_id = upsert_actor_mapping(
        emby_actor_id=req.emby_actor_id,
        emby_actor_name=req.emby_actor_name,
        javinfo_actress_id=req.javinfo_actress_id,
        javinfo_actress_name=req.javinfo_actress_name or "",
        confidence=req.confidence,
        status="candidate",
        source=req.source or "manual_search",
        javinfo_avatar_url=req.javinfo_avatar_url,
        movie_count=req.movie_count,
        confidence_breakdown=req.confidence_breakdown,
        confidence_label=req.confidence_label,
        risk_flags=req.risk_flags,
    )
    try:
        result = await review_actor_mapping_with_ai(
            emby_actor_id=req.emby_actor_id,
            emby_actor_name=req.emby_actor_name,
            candidate=req.model_dump(),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 判断失败: {exc}") from exc
    return {"success": True, "id": result.get("id") or mapping_id, **result}


@router.post("/actor-mappings/candidates/generate")
async def generate_mapping_candidates(
    search: Optional[str] = None,
    limit: int = 50,
    per_actor: int = 3,
    min_confidence: float = 0.55,
):
    """Generate actor-mapping candidates from Emby actor names."""
    from services.actor_mapping_candidates import generate_actor_mapping_candidates

    return await generate_actor_mapping_candidates(
        search=search,
        limit=limit,
        per_actor=per_actor,
        min_confidence=min_confidence,
    )


@router.post("/actor-mappings/auto-match")
async def auto_match_mappings(
    search: Optional[str] = None,
    limit: int = 500,
    dry_run: bool = False,
):
    """Conservatively auto-match Emby actors to JavInfo actresses."""
    from services.actor_mapping_candidates import auto_match_actor_mappings

    bounded_limit = max(1, min(int(limit or 500), 2000))
    result = await auto_match_actor_mappings(search=search, limit=bounded_limit, dry_run=dry_run)
    result.setdefault("limit", bounded_limit)
    return result


@router.post("/actor-mappings/confirm")
def confirm_mapping(req: ActorMappingRequest):
    """Confirm one Emby actor -> JavInfo actress mapping."""
    if not req.javinfo_actress_id:
        raise HTTPException(status_code=400, detail="javinfo_actress_id is required")
    from database import confirm_actor_mapping

    mapping_id = confirm_actor_mapping(
        emby_actor_id=req.emby_actor_id,
        emby_actor_name=req.emby_actor_name,
        javinfo_actress_id=req.javinfo_actress_id,
        javinfo_actress_name=req.javinfo_actress_name or "",
        confidence=req.confidence,
        source=req.source,
        javinfo_avatar_url=req.javinfo_avatar_url,
        movie_count=req.movie_count,
        confidence_breakdown=req.confidence_breakdown,
        confidence_label=req.confidence_label,
        risk_flags=req.risk_flags,
    )
    return {"success": True, "id": mapping_id}


@router.post("/actor-mappings/ignore")
def ignore_mapping(req: ActorMappingRequest):
    """Ignore one actor or one candidate mapping."""
    from database import ignore_actor_mapping

    mapping_id = ignore_actor_mapping(
        emby_actor_id=req.emby_actor_id,
        emby_actor_name=req.emby_actor_name,
        javinfo_actress_id=req.javinfo_actress_id,
        javinfo_actress_name=req.javinfo_actress_name,
        source=req.source,
        javinfo_avatar_url=req.javinfo_avatar_url,
        movie_count=req.movie_count,
        confidence_breakdown=req.confidence_breakdown,
        confidence_label=req.confidence_label,
        risk_flags=req.risk_flags,
    )
    return {"success": True, "id": mapping_id}


@router.delete("/actor-mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    """Delete an actor mapping or ignore record."""
    from database import delete_actor_mapping

    if not delete_actor_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"success": True}
