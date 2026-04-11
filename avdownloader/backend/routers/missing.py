from fastapi import APIRouter, HTTPException
from typing import Any
import json
from database import get_all_missing_summaries, get_missing_summary
from modules.emby_client import get_emby_client
from modules.info_client import get_info_client

router = APIRouter(prefix="/api/missing", tags=["missing"])

@router.get("/actresses")
async def list_missing_actresses() -> dict[str, Any]:
    """获取缺失演员摘要列表"""
    summaries = get_all_missing_summaries()
    return {
        "data": summaries,
        "total": len(summaries),
    }

@router.get("/actresses/{actress_id}")
async def get_missing_actress_detail(actress_id: int) -> dict[str, Any]:
    """获取某演员的缺失影片详情（按年份分组）"""
    summary = get_missing_summary(actress_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Actor not found in missing cache")

    # 解析 JSON 中的缺失影片
    videos = json.loads(summary.get("missing_videos_json", "[]"))

    # 按年份分组
    videos_by_year: dict[str, list] = {}
    for video in videos:
        year = video.get("release_date", "")[:4] if video.get("release_date") else "未知"
        if year not in videos_by_year:
            videos_by_year[year] = []
        videos_by_year[year].append(video)

    # 每组内按日期排序
    for year in videos_by_year:
        videos_by_year[year].sort(
            key=lambda x: x.get("release_date", ""),
            reverse=True
        )

    return {
        "actress_id": summary["actress_id"],
        "actress_name": summary["actress_name"],
        "missing_count": summary["missing_count"],
        "videos_by_year": videos_by_year,
    }

@router.post("/actresses/refresh")
async def refresh_missing_cache() -> dict[str, Any]:
    """刷新缺失演员缓存"""
    emby_client = get_emby_client()
    info_client = get_info_client()
    summaries = await emby_client.get_missing_actresses_summary(info_client)
    return {"status": "ok", "updated": len(summaries)}