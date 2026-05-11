"""库存对比 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import (
    get_inventory_actors, get_inventory_actor, get_inventory_videos,
    get_missing_videos, get_all_missing_videos, delete_missing_video,
    get_exempt_videos, add_exempt_video, delete_exempt_video, is_video_exempt,
    add_inventory_job, get_inventory_jobs, get_inventory_job,
    get_actor_aliases, add_actor_alias, get_canonical_actress_id, get_actor_primary_name, set_actor_primary_name,
    upsert_inventory_actor, upsert_inventory_video, add_missing_video, get_missing_count_by_actress,
    update_inventory_job, get_latest_snapshot_key, get_snapshot_actors,
    reassign_actress_movies, find_similar_actresses
)
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# === 作业 ===

class TriggerJobRequest(BaseModel):
    job_type: str
    actor_id: Optional[int] = None
    snapshot_key: Optional[str] = None

@router.post("/jobs/trigger")
async def trigger_job(req: TriggerJobRequest):
    """触发作业（collect=采集Emby快照，full/actor=对比）"""
    job_id = add_inventory_job(req.job_type, req.actor_id, req.snapshot_key)
    # 异步执行
    from scheduler.inventory_tasks import run_inventory_job
    run_inventory_job(job_id)
    return {"job_id": job_id, "status": "pending"}

@router.get("/snapshots/latest")
async def get_latest_snapshot():
    """获取最新快照信息"""
    from database import get_latest_snapshot_key, get_snapshot_actors
    key = get_latest_snapshot_key()
    if not key:
        return {"snapshot_key": None, "actors": []}
    actors = get_snapshot_actors(key)
    return {"snapshot_key": key, "actors": actors}

@router.get("/jobs")
async def list_jobs():
    """获取作业历史"""
    return {"data": get_inventory_jobs()}

@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
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

@router.get("/actors")
async def list_actors(
    search: str = None,
    sort_by: str = "actress_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50
):
    """获取库存演员列表（从 Emby 快照，含头像），支持搜索、排序、分页"""
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    # 排序字段映射
    sort_field = "actress_name"
    if sort_by == "total_videos":
        sort_field = "total_videos"
    elif sort_by == "missing_count":
        # missing_count 来自 inventory_actors，需特殊处理
        sort_field = None

    result = get_snapshot_actors(snapshot_key, search, sort_field, sort_order, page, page_size)

    # 读取对比统计（missing_count）
    inventory_map = {a["actress_id"]: a for a in get_inventory_actors()}
    enriched = []
    for actor in result["data"]:
        actress_id = actor["actress_id"]
        canon_id = get_canonical_actress_id(actress_id)
        primary = get_actor_primary_name(canon_id)
        inv = inventory_map.get(actress_id, {})
        image_tag = actor.get("image_tag", "")
        enriched.append({
            "actress_id": actress_id,
            "actress_name": actor["actress_name"],
            "display_name": primary or actor["actress_name"],
            "total_videos": actor.get("total_videos", 0),
            "missing_count": inv.get("missing_count", 0),
            "avatar_url": _emby_image_url(str(actress_id), image_tag),
        })

    # 如果按 missing_count 排序，在应用层排序
    if sort_by == "missing_count":
        reverse = sort_order == "desc"
        enriched.sort(key=lambda x: x["missing_count"], reverse=reverse)

    return {
        "data": enriched,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"]
    }

class MergeActorsRequest(BaseModel):
    from_actress_id: int
    to_actress_id: int

@router.post("/actors/merge-javhub")
async def merge_actors_javhub(req: MergeActorsRequest):
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


@router.get("/actor-mappings")
async def list_mappings(status: Optional[str] = None, q: Optional[str] = None, emby_actor_id: Optional[str] = None):
    """获取 Emby actor -> JavInfo actress 映射。"""
    from database import list_actor_mappings
    return {"data": list_actor_mappings(status=status, q=q, emby_actor_id=emby_actor_id)}


@router.get("/actor-mappings/summary")
async def actor_mapping_summary():
    """最新 Emby 快照的演员映射覆盖率。"""
    from database import mapping_summary
    snapshot_key = get_latest_snapshot_key()
    actors = get_snapshot_actors(snapshot_key, page_size=100000).get("data", []) if snapshot_key else []
    return {"snapshot_key": snapshot_key, **mapping_summary(actors)}


@router.get("/actor-mappings/unmapped")
async def list_unmapped_actor_mappings(search: Optional[str] = None, limit: int = 200):
    """列出最新快照中尚未确认/忽略的 Emby 演员。"""
    from database import list_actor_mappings
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": [], "total": 0, "snapshot_key": None}
    actors = get_snapshot_actors(snapshot_key, search=search, page_size=100000).get("data", [])
    decisions = {
        str(row["emby_actor_id"]): row
        for row in list_actor_mappings(limit=100000)
        if row.get("status") in ("confirmed", "ignored")
    }
    data = []
    for actor in actors:
        actor_id = str(actor.get("actress_id"))
        if actor_id in decisions:
            continue
        image_tag = actor.get("image_tag", "")
        data.append({
            "emby_actor_id": actor_id,
            "emby_actor_name": actor.get("actress_name", ""),
            "total_videos": actor.get("total_videos", 0),
            "avatar_url": _emby_image_url(actor_id, image_tag),
        })
        if len(data) >= limit:
            break
    return {"data": data, "total": len(data), "snapshot_key": snapshot_key}


@router.post("/actor-mappings/confirm")
async def confirm_mapping(req: ActorMappingRequest):
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
    )
    return {"success": True, "id": mapping_id}


@router.post("/actor-mappings/ignore")
async def ignore_mapping(req: ActorMappingRequest):
    """忽略某个 Emby 演员或某个候选映射。"""
    from database import ignore_actor_mapping
    mapping_id = ignore_actor_mapping(
        emby_actor_id=req.emby_actor_id,
        emby_actor_name=req.emby_actor_name,
        javinfo_actress_id=req.javinfo_actress_id,
        javinfo_actress_name=req.javinfo_actress_name,
        source=req.source,
    )
    return {"success": True, "id": mapping_id}


@router.delete("/actor-mappings/{mapping_id}")
async def delete_mapping(mapping_id: int):
    """解除映射/忽略记录。"""
    from database import delete_actor_mapping
    if not delete_actor_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"success": True}

@router.get("/actors/find-similar")
async def find_similar_actors(name: str = None, threshold: float = 0.6):
    """查找名字相似的演员（用于发现重复演员）"""
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"data": []}
    similar = find_similar_actresses(snapshot_key, name, threshold)
    # 补充 avatar_url
    for pair in similar:
        for actor_key in ("actor_a", "actor_b"):
            actor = pair[actor_key]
            actor["avatar_url"] = _emby_image_url(str(actor["actress_id"]), actor.get("image_tag", ""))
    return {"data": similar}

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
    from database import get_latest_snapshot_key, get_snapshot_actors
    avatar_url = ""
    emby_server_id = ""
    snapshot_key = get_latest_snapshot_key()
    if snapshot_key:
        snapshot_result = get_snapshot_actors(snapshot_key, page_size=100000)
        for a in snapshot_result.get("data", []):
            if a.get("actress_id") == actress_id:
                image_tag = a.get("image_tag", "")
                if image_tag:
                    avatar_url = _emby_image_url(str(actress_id), image_tag)
                break
        # 获取 Emby serverId
        from modules.emby_client import get_emby_client
        try:
            emby = get_emby_client()
            system_info = await emby._get("/System/Info")
            emby_server_id = system_info.get("Id", "")
        except Exception:
            pass

    return {
        **actor,
        "display_name": primary or actor["actress_name"],
        "videos": videos,
        "missing_videos": missing,
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
async def list_missing():
    """获取所有缺失影片"""
    return {"data": get_all_missing_videos()}

@router.get("/missing/{actress_id}")
async def list_missing_by_actor(actress_id: int):
    """按演员获取缺失影片"""
    return {"data": get_missing_videos(actress_id)}

@router.delete("/missing/{content_id}")
async def remove_missing(content_id: str):
    """移除缺失影片（补全后调用）"""
    delete_missing_video(content_id)
    return {"success": True}

# === 豁免 ===

@router.get("/exempt")
async def list_exempt():
    """获取豁免列表"""
    return {"data": get_exempt_videos()}

class ExemptRequest(BaseModel):
    content_id: str
    actress_id: int
    reason: str = ""

@router.post("/exempt")
async def exempt_video(req: ExemptRequest):
    """豁免影片"""
    add_exempt_video(req.content_id, req.actress_id, req.reason, "manual")
    delete_missing_video(req.content_id)
    return {"success": True}

@router.delete("/exempt/{content_id}")
async def unexempt_video(content_id: str):
    """撤销豁免"""
    delete_exempt_video(content_id)
    return {"success": True}

# === 归一化 ===

@router.get("/aliases")
async def list_aliases():
    """获取演员归一化映射"""
    return {"data": get_actor_aliases()}

class AliasRequest(BaseModel):
    alias_id: int
    canonical_id: int

@router.post("/aliases")
async def add_alias(req: AliasRequest):
    """添加演员归一化映射"""
    add_actor_alias(req.alias_id, req.canonical_id)
    return {"success": True}

@router.delete("/aliases/{alias_id}")
async def delete_alias(alias_id: int):
    """删除演员归一化映射"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM actor_aliases WHERE id = ?", (alias_id,))
    conn.commit()
    conn.close()
    return {"success": True}

class PrimaryNameRequest(BaseModel):
    actress_id: int
    primary_name: str

@router.put("/actors/{actress_id}/primary-name")
async def set_primary_name(actress_id: int, req: PrimaryNameRequest):
    """设置演员主显示名"""
    set_actor_primary_name(actress_id, req.primary_name)
    return {"success": True}

# === 补全 ===

@router.post("/fill/{content_id}")
async def fill_video(content_id: str):
    """将单个缺失影片转为下载候选，不直接下发下载。"""
    from database import upsert_download_candidate
    info = get_info_client()
    candidate = None
    try:
        video = await info.get_video(content_id)
        candidate = upsert_download_candidate(
            content_id=video.get("content_id") or video.get("dvd_id") or content_id,
            dvd_id=video.get("dvd_id") or content_id,
            title=video.get("title_ja") or video.get("title_en") or video.get("title") or "",
            actress_id=None,
            actress_name=None,
            jacket_thumb_url=video.get("jacket_thumb_url") or video.get("jacket_full_url"),
            release_date=video.get("release_date"),
            source="inventory",
            reason="inventory_fill",
        )
        delete_missing_video(content_id)
    except Exception:
        candidate = upsert_download_candidate(
            content_id=content_id,
            dvd_id=content_id,
            title=content_id,
            source="inventory",
            reason="inventory_fill_fallback",
        )
        delete_missing_video(content_id)
    return {"success": True, "candidate": candidate}

@router.post("/fill-all")
async def fill_all_videos():
    """将所有缺失影片转为下载候选，不直接下发下载。"""
    from database import upsert_download_candidate
    missing = get_all_missing_videos()
    info = get_info_client()
    count = 0
    candidates = []
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
        candidates.append(candidate)
        delete_missing_video(content_id)
        count += 1
    return {"success": True, "count": count, "candidates": candidates}
