"""把自有云盘文件索引导出为 inventory snapshot。

复用既有 snapshot 表与对比管线（零改动）：
- emby_item_id 用合成 id ``lib:{file_id}``（与 Emby item id 不冲突）。
- actress_id 直接使用 JavInfo 演员 id，并写入 confirmed 身份映射
  （emby_actor_id == javinfo_actress_id），使 compare 阶段的
  get_confirmed_actor_mapping 查找天然命中，不需要人工映射。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from database import (
    create_snapshot_key,
    list_matched_library_files,
    save_emby_actors_snapshot,
    save_emvy_snapshot,
)
from database.actor_mapping import upsert_actor_mapping
from database.inventory import upsert_inventory_actor

logger = logging.getLogger(__name__)

METADATA_CONCURRENCY = 8


def _actress_display_name(actress: dict) -> str:
    return str(
        actress.get("name_kanji")
        or actress.get("name_romaji")
        or actress.get("name_kana")
        or actress.get("name")
        or ""
    ).strip()


async def build_library_snapshot(progress_cb: Optional[Callable[[int], None]] = None) -> dict:
    """从 library_files 构建快照。返回统计 dict（含 snapshot_key）。"""
    from modules.info_client import get_info_client

    def report(pct: int) -> None:
        if progress_cb:
            try:
                progress_cb(pct)
            except Exception:
                pass

    files = list_matched_library_files()
    report(5)

    # 按番号归并多版本文件，元数据每番号只取一次
    by_code: dict[str, list[dict]] = {}
    for row in files:
        by_code.setdefault(row["content_id"], []).append(row)

    client = get_info_client()
    sem = asyncio.Semaphore(METADATA_CONCURRENCY)

    async def fetch(code: str):
        async with sem:
            try:
                return code, await client.get_video(code)
            except Exception:
                return code, None

    results = await asyncio.gather(*(fetch(code) for code in by_code))
    report(40)

    # 聚合为 actors_data（与 Emby collect 同构）
    actors: dict[int, dict] = {}
    no_metadata = 0
    no_actress = 0
    video_total = 0
    for code, video in results:
        if not video:
            no_metadata += 1
            continue
        actresses = video.get("actresses") or []
        if not actresses:
            no_actress += 1
            continue
        video_total += 1
        title = str(video.get("title_ja") or video.get("title_en") or code)
        for actress in actresses:
            actress_id = actress.get("id")
            name = _actress_display_name(actress)
            if not actress_id or not name:
                continue
            bucket = actors.setdefault(int(actress_id), {
                "actress_id": int(actress_id),
                "actress_name": name,
                "items": [],
            })
            for row in by_code[code]:
                bucket["items"].append({
                    "item_id": f"lib:{row['id']}",
                    "title": title,
                    "filename": row["name"],
                })

    snapshot_key = create_snapshot_key()
    actors_data = list(actors.values())
    for actor in actors_data:
        actor["video_count"] = len(actor["items"])
    save_emby_actors_snapshot(snapshot_key, actors_data)
    report(55)

    processed = 0
    total_items = sum(len(a["items"]) for a in actors_data)
    for actor in actors_data:
        for item in actor["items"]:
            save_emvy_snapshot(
                snapshot_key=snapshot_key,
                actress_id=actor["actress_id"],
                actress_name=actor["actress_name"],
                emby_item_id=item["item_id"],
                title=item["title"],
                filename=item["filename"],
            )
            processed += 1
            if total_items and processed % max(1, total_items // 10) == 0:
                report(55 + int(30 * processed / total_items))

    # 身份映射 + inventory_actors 同步，让 compare 阶段零改动可用
    for actor in actors_data:
        upsert_inventory_actor(actor["actress_id"], actor["actress_name"])
        try:
            upsert_actor_mapping(
                emby_actor_id=actor["actress_id"],
                emby_actor_name=actor["actress_name"],
                javinfo_actress_id=actor["actress_id"],
                javinfo_actress_name=actor["actress_name"],
                confidence=1.0,
                status="confirmed",
                source="library",
            )
        except Exception:
            logger.exception("identity mapping upsert failed for %s", actor["actress_id"])
    report(95)

    stats = {
        "snapshot_key": snapshot_key,
        "mode": "library",
        "actors": len(actors_data),
        "videos": video_total,
        "files": len(files),
        "no_metadata": no_metadata,
        "no_actress": no_actress,
    }
    logger.info("[LibrarySnapshot] built %s", stats)
    return stats


async def diff_library_vs_emby(emby_snapshot_key: str, library_snapshot_key: str) -> dict:
    """切换基准前的人工核对：输出两个快照番号集合的差异。"""
    from database.snapshot import iter_snapshot_videos_by_actor
    from modules.code_matcher import extract_code

    def codes_of(snapshot_key: str) -> set[str]:
        codes: set[str] = set()
        for video in iter_snapshot_videos_by_actor(snapshot_key, limit=100000):
            code = extract_code(video.get("filename") or "") or extract_code(video.get("title") or "")
            if code:
                codes.add(code)
        return codes

    emby_codes = codes_of(emby_snapshot_key)
    library_codes = codes_of(library_snapshot_key)
    return {
        "emby_total": len(emby_codes),
        "library_total": len(library_codes),
        "only_in_emby": sorted(emby_codes - library_codes),
        "only_in_library": sorted(library_codes - emby_codes),
    }
