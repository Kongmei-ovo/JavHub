"""库存对比定时任务"""
from __future__ import annotations
import asyncio
from typing import Optional
from backend.database import (
    add_inventory_job, update_inventory_job, get_inventory_job,
    upsert_inventory_actor, upsert_inventory_video, add_missing_video,
    update_inventory_actor_stats, get_exempt_videos,
    get_inventory_actors
)
from backend.modules.emby_client import get_emby_client
from backend.modules.info_client import get_info_client


def is_exempt(content_id: str) -> bool:
    """检查影片是否被豁免"""
    exempt_list = get_exempt_videos()
    return any(v["content_id"] == content_id for v in exempt_list)


async def run_full_comparison(job_id: int):
    """全量对比作业"""
    update_inventory_job(job_id, "running")
    try:
        emby = get_emby_client()
        info = get_info_client()

        # 1. 拉取 Emby 所有演员
        emby_actors = await emby.get_all_actresses()

        # 2. 存储演员到 inventory_actors
        for actor in emby_actors:
            upsert_inventory_actor(actor["actress_id"], actor["actress_name"])

        # 3. 按演员对比 JavInfo
        for actor in emby_actors:
            actress_id = actor["actress_id"]
            total = 0
            missing = 0

            try:
                result = await info.get_actress_videos(actress_id, page_size=999)
                javinfo_videos = result.get("data", [])
            except Exception:
                continue

            emby_videos = await emby.get_actress_videos(actress_id)
            emby_codes = {v.get("FileName", "").split(".")[0].upper() for v in emby_videos}

            for video in javinfo_videos:
                content_id = video.get("content_id", "").upper()
                if not content_id:
                    continue

                total += 1
                in_emby = content_id in emby_codes or any(content_id in fn.upper() for fn in emby_codes)

                if is_exempt(content_id):
                    continue

                if not in_emby:
                    add_missing_video(
                        content_id=video.get("content_id", ""),
                        actress_id=actress_id,
                        title=video.get("title_en", ""),
                        release_date=video.get("release_date"),
                        jacket_thumb_url=video.get("jacket_thumb_url"),
                    )
                    missing += 1

                for emby_v in emby_videos:
                    emby_fn = emby_v.get("FileName", "")
                    if content_id in emby_fn.upper():
                        upsert_inventory_video(
                            content_id=video.get("content_id", ""),
                            emby_item_id=emby_v.get("Id", ""),
                            actress_id=actress_id,
                            title=video.get("title_en", ""),
                            release_date=video.get("release_date"),
                            jacket_thumb_url=video.get("jacket_thumb_url"),
                        )
                        break

            update_inventory_actor_stats(actress_id, total, missing)

        update_inventory_job(job_id, "completed")

    except Exception as e:
        update_inventory_job(job_id, "failed", str(e))


async def run_actor_comparison(job_id: int, actor_id: int):
    """单演员增量对比"""
    update_inventory_job(job_id, "running")
    try:
        emby = get_emby_client()
        info = get_info_client()

        actor = get_inventory_actor(actor_id)
        if not actor:
            update_inventory_job(job_id, "failed", "Actor not found")
            return

        actress_id = actor["actress_id"]

        result = await info.get_actress_videos(actress_id, page_size=999)
        javinfo_videos = result.get("data", [])

        emby_videos = await emby.get_actress_videos(actress_id)
        emby_codes = {v.get("FileName", "").split(".")[0].upper() for v in emby_videos}

        total = len(javinfo_videos)
        new_missing = 0

        for video in javinfo_videos:
            content_id = video.get("content_id", "").upper()
            if not content_id:
                continue

            if is_exempt(content_id):
                continue

            in_emby = content_id in emby_codes or any(content_id in fn.upper() for fn in emby_codes)

            if not in_emby:
                add_missing_video(
                    content_id=video.get("content_id", ""),
                    actress_id=actress_id,
                    title=video.get("title_en", ""),
                    release_date=video.get("release_date"),
                    jacket_thumb_url=video.get("jacket_thumb_url"),
                )
                new_missing += 1

        current_missing = get_inventory_actor(actor_id)["missing_count"]
        update_inventory_actor_stats(actress_id, total, current_missing + new_missing)

        update_inventory_job(job_id, "completed")

    except Exception as e:
        update_inventory_job(job_id, "failed", str(e))


async def run_inventory_comparison(job_type: str = "full", actor_id: int | None = None):
    """定时任务入口"""
    job_id = add_inventory_job(job_type, actor_id)
    if job_type == "full":
        await run_full_comparison(job_id)
    else:
        await run_actor_comparison(job_id, actor_id)
