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
    update_inventory_job
)
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# === 作业 ===

class TriggerJobRequest(BaseModel):
    job_type: str
    actor_id: Optional[int] = None

@router.post("/jobs/trigger")
async def trigger_job(req: TriggerJobRequest):
    """触发对比作业"""
    job_id = add_inventory_job(req.job_type, req.actor_id)
    return {"job_id": job_id, "status": "pending"}

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

@router.get("/actors")
async def list_actors():
    """获取库存演员列表"""
    actors = get_inventory_actors()
    result = []
    for actor in actors:
        canon_id = get_canonical_actress_id(actor["actress_id"])
        primary = get_actor_primary_name(canon_id)
        result.append({
            **actor,
            "display_name": primary or actor["actress_name"],
        })
    return {"data": result}

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
    return {
        **actor,
        "display_name": primary or actor["actress_name"],
        "videos": videos,
        "missing_videos": missing,
    }

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
    """补全单个缺失影片"""
    from services.downloader import create_download_task
    info = get_info_client()
    try:
        video = await info.get_video(content_id)
        magnets = video.get("magnets", [])
        if magnets:
            magnet = magnets[0].get("magnet", "")
            create_download_task(content_id, video.get("title_en", ""), magnet)
        delete_missing_video(content_id)
    except Exception:
        pass
    delete_missing_video(content_id)
    return {"success": True}

@router.post("/fill-all")
async def fill_all_videos():
    """一键补全所有缺失影片"""
    from services.downloader import create_download_task
    missing = get_all_missing_videos()
    info = get_info_client()
    count = 0
    for v in missing:
        try:
            video = await info.get_video(v["content_id"])
            magnets = video.get("magnets", [])
            if magnets:
                magnet = magnets[0].get("magnet", "")
                create_download_task(v["content_id"], video.get("title_en", ""), magnet)
        except Exception:
            pass
        delete_missing_video(v["content_id"])
        count += 1
    return {"success": True, "count": count}