"""库存对比 API 路由"""
import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import (
    get_inventory_actors, get_inventory_actors_by_ids, get_inventory_actor, get_inventory_videos,
    get_missing_videos, get_all_missing_videos, get_missing_video, list_missing_videos_page, delete_missing_video,
    get_exempt_videos, add_exempt_video, delete_exempt_video,
    add_inventory_job, get_inventory_jobs, get_inventory_job,
    get_actor_aliases, add_actor_alias, get_canonical_actress_id, get_actor_primary_name,
    set_actor_primary_name, get_latest_snapshot_key, count_snapshot_actors, get_snapshot_actor, get_snapshot_actors,
    list_actor_mappings_for_actor_ids,
    find_similar_actresses, list_download_candidates, list_download_candidates_page, count_download_candidates,
    download_candidate_summary, download_candidate_stats, mapping_summary_for_snapshot
)
from database.base import get_db
from modules.info_client import get_info_client
from routers.duplicates import _snapshot_duplicates
from services.cache import get_or_set_response, should_bypass_response_cache

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# === 作业 ===

class TriggerJobRequest(BaseModel):
    job_type: str
    actor_id: Optional[int] = None
    snapshot_key: Optional[str] = None

@router.post("/jobs/trigger")
def trigger_job(req: TriggerJobRequest):
    """触发作业（collect=采集Emby快照，full/actor=对比）"""
    job_id = add_inventory_job(req.job_type, req.actor_id, req.snapshot_key)
    # 异步执行
    from scheduler.inventory_tasks import run_inventory_job
    run_inventory_job(job_id)
    return {"job_id": job_id, "status": "pending"}

@router.get("/snapshots/latest")
def get_latest_snapshot(include_actors: bool = False):
    """获取最新快照信息"""
    key = get_latest_snapshot_key()
    if not key:
        return {
            "snapshot_key": None,
            "actor_count": 0,
            "actors": {"data": [], "total": 0, "deferred": True},
        }
    actor_count = count_snapshot_actors(key)
    if include_actors:
        return {
            "snapshot_key": key,
            "actor_count": actor_count,
            "actors": get_snapshot_actors(key),
        }
    return {
        "snapshot_key": key,
        "actor_count": actor_count,
        "actors": {"data": [], "total": actor_count, "deferred": True},
    }

@router.get("/jobs")
def list_jobs():
    """获取作业历史"""
    return {"data": get_inventory_jobs()}

@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    """获取单个作业详情"""
    job = get_inventory_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# === 演员 ===

def _emby_image_url(actress_id: str, image_tag: str) -> str:
    """构造 Emby 演员头像 URL（无需api_key，Emby默认允许公开访问图片）"""
    if not image_tag:
        return ""
    from config import config
    emby_cfg = getattr(config, "emby", {})
    api_url = emby_cfg.get("api_url", "").rstrip("/")
    return f"{api_url}/Items/{actress_id}/Images/Primary?tag={image_tag}"


def _actor_sort_params(actor_sort: str) -> tuple[str, str]:
    if actor_sort == "total_videos":
        return "total_videos", "desc"
    if actor_sort == "missing_count":
        return "missing_count", "desc"
    return "actress_name", "asc"


def _actor_sort_field(sort_by: str | None) -> str:
    if sort_by in {"total_videos", "missing_count"}:
        return sort_by
    return "actress_name"


def _resolve_canonical_id(actress_id: int, alias_map: dict[int, int]) -> int:
    current = actress_id
    seen: set[int] = set()
    while current in alias_map and current not in seen:
        seen.add(current)
        current = alias_map[current]
    return current


def _alias_map() -> dict[int, int]:
    aliases: dict[int, int] = {}
    for row in get_actor_aliases():
        try:
            aliases[int(row["alias_id"])] = int(row["canonical_id"])
        except (KeyError, TypeError, ValueError):
            continue
    return aliases


def _enrich_snapshot_actor(actor: dict, inventory_map: dict, alias_map: dict[int, int]) -> dict:
    actress_id = actor["actress_id"]
    canon_id = _resolve_canonical_id(int(actress_id), alias_map)
    inv = inventory_map.get(actress_id, {})
    canonical_inv = inventory_map.get(canon_id, {})
    primary = canonical_inv.get("primary_name") or ""
    image_tag = actor.get("image_tag", "")
    return {
        "actress_id": actress_id,
        "actress_name": actor["actress_name"],
        "display_name": primary or actor["actress_name"],
        "total_videos": actor.get("total_videos", 0),
        "missing_count": inv.get("missing_count", 0),
        "avatar_url": _emby_image_url(str(actress_id), image_tag),
    }


def _inventory_actors_payload(
    snapshot_key: str | None,
    search: str | None = None,
    actor_sort: str = "missing_count",
    sort_by: str | None = None,
    sort_order: str | None = None,
    page: int = 1,
    page_size: int = 60,
) -> dict:
    if not snapshot_key:
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    if sort_by is not None or sort_order is not None:
        sort_field = _actor_sort_field(sort_by)
        order = "asc" if sort_order == "asc" else "desc"
    else:
        sort_field, order = _actor_sort_params(actor_sort)
    result = get_snapshot_actors(
        snapshot_key,
        search=search,
        sort_by=sort_field,
        sort_order=order,
        page=page,
        page_size=page_size,
    )
    aliases = _alias_map()
    actor_ids = sorted({int(actor["actress_id"]) for actor in result["data"]})
    canonical_ids = sorted({_resolve_canonical_id(actor_id, aliases) for actor_id in actor_ids})
    inventory_ids = sorted({*actor_ids, *canonical_ids})
    inventory_map = {a["actress_id"]: a for a in get_inventory_actors_by_ids(inventory_ids)}
    enriched = [_enrich_snapshot_actor(actor, inventory_map, aliases) for actor in result["data"]]
    if sort_field == "missing_count":
        enriched.sort(key=lambda item: item["missing_count"], reverse=order == "desc")
    return {
        "data": enriched,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


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
    """片库整理首屏聚合，减少前端初始化时的接口扇出。"""
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
        "snapshot": {
            "snapshot_key": snapshot_key,
            "actor_count": snapshot_actor_count,
        },
        "actors": _inventory_actors_payload(
            snapshot_key,
            search=actor_search,
            actor_sort=actor_sort,
            page=1,
            page_size=60,
        ),
        "mapping": {
            "summary": mapping_summary_for_snapshot(snapshot_key),
            "unmapped": _unmapped_actor_mappings_payload(
                search=mapping_search,
                limit=80,
                snapshot_key=snapshot_key,
            ),
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
        "duplicates": {
            "data": [],
            "total": 0,
            "deferred": True,
        },
        "jobs": {
            "data": get_inventory_jobs(limit=50),
        },
    }

@router.get("/actors")
async def list_actors(
    search: str = None,
    sort_by: str = "actress_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    cache_control: Optional[str] = Query(None, alias="cache"),
):
    """获取库存演员列表（从 Emby 快照，含头像），支持搜索、排序、分页"""
    params = {
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": page_size,
    }

    async def produce() -> dict:
        return await asyncio.to_thread(
            _list_actors_payload,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

    return await get_or_set_response(
        "inventory_actors",
        params,
        produce,
        ttl=10,
        bypass=should_bypass_response_cache(cache_control),
    )


def _list_actors_payload(
    search: str = None,
    sort_by: str = "actress_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    return _inventory_actors_payload(
        snapshot_key,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

class MergeActorsRequest(BaseModel):
    from_actress_id: int
    to_actress_id: int

@router.post("/actors/merge-javhub")
def merge_actors_javhub(req: MergeActorsRequest):
    """JavHub 映射层合并：只建立 alias 映射，不动电影数据，不碰 JavInfo 库"""
    if req.from_actress_id == req.to_actress_id:
        raise HTTPException(status_code=400, detail="不能合并到自身")
    add_actor_alias(req.from_actress_id, req.to_actress_id)
    return {"success": True, "from": req.from_actress_id, "to": req.to_actress_id, "type": "javhub_mapping"}


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


@router.get("/actor-mappings")
def list_mappings(
    status: Optional[str] = None,
    q: Optional[str] = None,
    emby_actor_id: Optional[str] = None,
    limit: int = 200,
):
    """获取 Emby actor -> JavInfo actress 映射。"""
    from database import list_actor_mappings
    return {"data": list_actor_mappings(status=status, q=q, emby_actor_id=emby_actor_id, limit=limit)}


@router.get("/actor-mappings/summary")
def actor_mapping_summary():
    """最新 Emby 快照的演员映射覆盖率。"""
    snapshot_key = get_latest_snapshot_key()
    return {"snapshot_key": snapshot_key, **mapping_summary_for_snapshot(snapshot_key)}


@router.get("/actor-mappings/unmapped")
def list_unmapped_actor_mappings(search: Optional[str] = None, limit: int = 200):
    """列出最新快照中尚未确认/忽略的 Emby 演员，并附带待审候选。"""
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
    """映射专用 JavInfo 查找，返回统一候选结构。"""
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
    """文本 AI 辅助判断 Emby 演员和 JavInfo 演员是否同一人。"""
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
    """按 Emby 演员名搜索 JavInfo，生成待确认映射候选。"""
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
    """保守自动匹配 Emby 演员到 JavInfo 演员。"""
    from services.actor_mapping_candidates import auto_match_actor_mappings
    bounded_limit = max(1, min(int(limit or 500), 2000))
    result = await auto_match_actor_mappings(
        search=search,
        limit=bounded_limit,
        dry_run=dry_run,
    )
    result.setdefault("limit", bounded_limit)
    return result


@router.post("/actor-mappings/confirm")
def confirm_mapping(req: ActorMappingRequest):
    """确认 Emby 演员映射到 JavInfo 演员。"""
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
    """忽略某个 Emby 演员或某个候选映射。"""
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
    """解除映射/忽略记录。"""
    from database import delete_actor_mapping
    if not delete_actor_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"success": True}

@router.get("/actors/find-similar")
def find_similar_actors(
    name: str = None,
    threshold: float = 0.6,
    limit: int = Query(50, ge=1, le=200),
    candidate_limit: int = Query(250, ge=2, le=1000),
):
    """查找名字相似的演员（用于发现重复演员）"""
    bounded_limit = max(1, min(int(limit or 50), 200))
    bounded_candidate_limit = max(2, min(int(candidate_limit or 250), 1000))
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "limit": bounded_limit, "candidate_limit": bounded_candidate_limit}
    similar = find_similar_actresses(
        snapshot_key,
        name,
        threshold,
        limit=bounded_limit,
        candidate_limit=bounded_candidate_limit,
    )
    # 补充 avatar_url
    for pair in similar:
        for actor_key in ("actor_a", "actor_b"):
            actor = pair[actor_key]
            actor["avatar_url"] = _emby_image_url(str(actor["actress_id"]), actor.get("image_tag", ""))
    return {"data": similar, "limit": bounded_limit, "candidate_limit": bounded_candidate_limit}

@router.get("/actors/{actress_id}")
async def get_actor(actress_id: int):
    """获取演员详情（含影片列表）"""
    actor = get_inventory_actor(actress_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    videos = get_inventory_videos(actress_id)
    missing = get_missing_videos(actress_id)
    canon_id = get_canonical_actress_id(actress_id)
    primary = get_actor_primary_name(canon_id)
    from database import get_confirmed_actor_mapping
    mapping = get_confirmed_actor_mapping(actress_id)

    # 获取 Emby 配置（用于前端构造图片 URL）
    from config import config
    emby_cfg = getattr(config, "emby", {})
    emby_api_url = emby_cfg.get("api_url", "").rstrip("/")
    # Web URL 从 api_url 推断（去掉 /emby 或端口换为 8096）
    emby_web_url = emby_cfg.get("web_url", "")
    if not emby_web_url and emby_api_url:
        # 默认用 8096 端口
        import re
        match = re.match(r'(https?://[^:]+)', emby_api_url)
        if match:
            emby_web_url = f"{match.group(1)}:8096"

    # 获取演员头像 URL 和 Emby serverId
    from database import get_latest_snapshot_key, get_snapshot_actor
    avatar_url = ""
    emby_server_id = ""
    snapshot_key = get_latest_snapshot_key()
    if snapshot_key:
        snapshot_actor = get_snapshot_actor(snapshot_key, actress_id)
        image_tag = snapshot_actor.get("image_tag", "") if snapshot_actor else ""
        if image_tag:
            avatar_url = _emby_image_url(str(actress_id), image_tag)
        # 获取 Emby serverId
        from modules.emby_client import get_emby_client
        try:
            emby = get_emby_client()
            system_info = await emby._get("/System/Info")
            emby_server_id = system_info.get("Id", "")
        except Exception:
            emby_server_id = ""

    return {
        **actor,
        "display_name": primary or actor["actress_name"],
        "videos": videos,
        "missing_videos": missing,
        "mapping_status": "confirmed" if mapping else "unmapped",
        "actor_mapping": mapping,
        "avatar_url": avatar_url,
        "_emby_api_url": emby_api_url,
        "_emby_web_url": emby_web_url,
        "_emby_server_id": emby_server_id,
    }

@router.get("/actors/{actress_id}/emby-videos")
async def get_actor_emby_videos(actress_id: int):
    """从 Emby 实时获取演员的影片列表"""
    from modules.emby_client import get_emby_client
    emby = get_emby_client()
    try:
        items = await emby.get_actress_videos(actress_id)
        # 提取关键字段并按发布年份排序
        videos = []
        for item in items:
            videos.append({
                "item_id": item.get("Id"),
                "title": item.get("Name"),
                "filename": item.get("FileName"),
                "production_year": item.get("ProductionYear"),
                "premiere_date": item.get("PremiereDate"),
                "image_tag": item.get("ImageTags", {}).get("Primary"),
            })
        # 编年正序：最早的年份/日期在前
        videos.sort(key=lambda x: (
            x.get("production_year") or 9999,
            x.get("premiere_date") or ""
        ))
        return {"data": videos, "total": len(videos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Emby影片失败: {str(e)}")

# === 缺失影片 ===

@router.get("/missing")
def list_missing(page: int = 1, page_size: int = 80):
    """分页获取缺失影片。"""
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
    """按演员获取缺失影片"""
    return {"data": get_missing_videos(actress_id)}

@router.delete("/missing/{content_id}")
def remove_missing(content_id: str):
    """移除缺失影片（补全后调用）"""
    delete_missing_video(content_id)
    return {"success": True}

# === 豁免 ===

@router.get("/exempt")
def list_exempt():
    """获取豁免列表"""
    return {"data": get_exempt_videos()}

class ExemptRequest(BaseModel):
    content_id: str
    actress_id: int
    reason: str = ""

@router.post("/exempt")
def exempt_video(req: ExemptRequest):
    """豁免影片"""
    add_exempt_video(req.content_id, req.actress_id, req.reason, "manual")
    delete_missing_video(req.content_id)
    return {"success": True}

@router.delete("/exempt/{content_id}")
def unexempt_video(content_id: str):
    """撤销豁免"""
    delete_exempt_video(content_id)
    return {"success": True}

# === 归一化 ===

@router.get("/aliases")
def list_aliases():
    """获取演员归一化映射"""
    return {"data": get_actor_aliases()}

class AliasRequest(BaseModel):
    alias_id: int
    canonical_id: int

@router.post("/aliases")
def add_alias(req: AliasRequest):
    """添加演员归一化映射"""
    add_actor_alias(req.alias_id, req.canonical_id)
    return {"success": True}

@router.delete("/aliases/{alias_id}")
def delete_alias(alias_id: int):
    """删除演员归一化映射"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actor_aliases WHERE id = ?", (alias_id,))
    return {"success": True}

class PrimaryNameRequest(BaseModel):
    actress_id: int
    primary_name: str

@router.put("/actors/{actress_id}/primary-name")
def set_primary_name(actress_id: int, req: PrimaryNameRequest):
    """设置演员主显示名"""
    set_actor_primary_name(actress_id, req.primary_name)
    return {"success": True}

# === 补全 ===

def _find_missing_video(content_id: str) -> Optional[dict]:
    return get_missing_video(content_id)

@router.post("/fill/{content_id}")
async def fill_video(content_id: str):
    """将单个缺失影片转为下载候选，不直接下发下载。"""
    from database import upsert_download_candidate
    missing_video = _find_missing_video(content_id) or {}
    info = get_info_client()
    candidate = None
    try:
        video = await info.get_video(content_id)
        candidate = upsert_download_candidate(
            content_id=video.get("content_id") or video.get("dvd_id") or content_id,
            dvd_id=video.get("dvd_id") or content_id,
            title=video.get("title_ja") or video.get("title_en") or video.get("title") or missing_video.get("title") or "",
            actress_id=missing_video.get("actress_id"),
            actress_name=None,
            jacket_thumb_url=video.get("jacket_thumb_url") or video.get("jacket_full_url") or missing_video.get("jacket_thumb_url"),
            release_date=video.get("release_date") or missing_video.get("release_date"),
            source="inventory",
            reason="inventory_fill",
        )
    except Exception:
        candidate = upsert_download_candidate(
            content_id=content_id,
            dvd_id=content_id,
            title=missing_video.get("title") or content_id,
            actress_id=missing_video.get("actress_id"),
            jacket_thumb_url=missing_video.get("jacket_thumb_url"),
            release_date=missing_video.get("release_date"),
            source="inventory",
            reason="inventory_fill_fallback",
        )
    return {"success": True, "candidate": candidate}

@router.post("/fill-all")
async def fill_all_videos(limit: int = 100, offset: int = 0, sample_limit: int = 20):
    """将一页缺失影片转为下载候选，不直接下发下载。"""
    from database import upsert_download_candidate
    safe_limit = max(1, min(int(limit or 100), 100))
    safe_offset = max(0, int(offset or 0))
    page = list_missing_videos_page(limit=safe_limit, offset=safe_offset)
    missing = page["data"]
    total = int(page.get("total") or 0)
    page_limit = int(page.get("limit") or safe_limit)
    page_offset = int(page.get("offset") or safe_offset)
    info = get_info_client()
    count = 0
    candidates = []
    safe_sample_limit = max(0, min(int(sample_limit or 0), 100))
    for v in missing:
        content_id = v["content_id"]
        try:
            video = await info.get_video(content_id)
            candidate = upsert_download_candidate(
                content_id=video.get("content_id") or video.get("dvd_id") or content_id,
                dvd_id=video.get("dvd_id") or content_id,
                title=video.get("title_ja") or video.get("title_en") or video.get("title") or v.get("title") or "",
                actress_id=v.get("actress_id"),
                actress_name=None,
                jacket_thumb_url=video.get("jacket_thumb_url") or video.get("jacket_full_url") or v.get("jacket_thumb_url"),
                release_date=video.get("release_date") or v.get("release_date"),
                source="inventory",
                reason="inventory_fill_all",
            )
        except Exception:
            candidate = upsert_download_candidate(
                content_id=content_id,
                dvd_id=content_id,
                title=v.get("title") or content_id,
                actress_id=v.get("actress_id"),
                jacket_thumb_url=v.get("jacket_thumb_url"),
                release_date=v.get("release_date"),
                source="inventory",
                reason="inventory_fill_all_fallback",
            )
        if len(candidates) < safe_sample_limit:
            candidates.append(candidate)
        count += 1
    return {
        "success": True,
        "count": count,
        "total": total,
        "limit": page_limit,
        "offset": page_offset,
        "has_more": page_offset + count < total,
        "sample_count": len(candidates),
        "truncated": count > len(candidates),
        "candidates": candidates,
    }
