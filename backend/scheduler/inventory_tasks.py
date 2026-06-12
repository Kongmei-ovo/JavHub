"""库存对比定时任务 - 两阶段设计"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from database import (
    add_inventory_job, update_inventory_job, update_inventory_progress, get_inventory_job,
    upsert_inventory_actor, add_missing_video,
    update_inventory_actor_stats, get_exempt_videos, upsert_inventory_video,
    create_snapshot_key,
    save_emby_actors_snapshot, save_emvy_snapshot,
    get_latest_snapshot_key, get_snapshot_actors, get_snapshot_videos,
    get_confirmed_actor_mapping
)
from database.snapshot import (
    clone_snapshot,
    delete_emby_snapshot_rows,
    get_emby_item_ids_for_snapshot,
    get_snapshot_created_at,
    prune_old_snapshots,
    upsert_emvy_snapshot,
)
from config import config
from modules.emby_client import get_emby_client
from services.watchlist_pipeline import WatchlistPipeline, video_code, video_in_snapshot_match


logger = logging.getLogger(__name__)


def is_exempt(content_id: str) -> bool:
    """检查影片是否被豁免（保留旧 API；内部循环请改用 ``_load_exempt_set``）。"""
    exempt_list = get_exempt_videos()
    return any(v["content_id"] == content_id for v in exempt_list)


def _load_exempt_set() -> set[str]:
    """Snapshot exempt list once per job — avoids the N+1 full-table scan."""
    return {row["content_id"] for row in get_exempt_videos() if row.get("content_id")}


def _video_content_id(video: dict) -> str:
    return video.get("content_id") or video.get("dvd_id", "")


def _video_title(video: dict) -> str:
    return video.get("title_ja") or video.get("title_en") or video.get("title") or ""


def _missing_provenance(snapshot_key: str) -> dict:
    return {
        "snapshot_key": snapshot_key,
        "matched_emby_item_id": None,
        "matched_filename": None,
    }


def _record_owned_video(video: dict, actress_id: int, matched: dict) -> None:
    emby_item_id = matched.get("emby_item_id") or matched.get("Id") or ""
    if not emby_item_id:
        return
    upsert_inventory_video(
        content_id=_video_content_id(video),
        emby_item_id=emby_item_id,
        actress_id=actress_id,
        title=_video_title(video) or matched.get("title") or matched.get("Name") or "",
        release_date=video.get("release_date"),
        jacket_thumb_url=video.get("jacket_thumb_url") or video.get("jacket_full_url"),
        matched_filename=matched.get("filename") or matched.get("FileName"),
    )


def run_inventory_job(job_id: int, mode: str = "full"):
    """提交作业到共享后台事件循环（非阻塞，立即返回）。"""
    from scheduler.worker_loop import submit
    submit(_execute_job(job_id, mode=mode), kind="inventory", label=f"Inventory {job_id}")


async def _execute_job(job_id: int, mode: str = "full"):
    """在共享后台事件循环上执行作业。"""
    job = get_inventory_job(job_id)
    if not job:
        logger.warning("[Inventory] Job %s not found", job_id)
        return

    job_type = job["job_type"]
    try:
        if job_type == "collect":
            await run_collect_job(job_id, mode=mode)
        elif job_type == "full":
            await run_compare_job(job_id, job.get("snapshot_key"))
        elif job_type == "actor":
            await run_actor_compare_job(job_id, job["actor_id"], job.get("snapshot_key"))
        else:
            update_inventory_job(job_id, "failed", f"Unknown job type: {job_type}")
    except Exception:
        logger.exception("[Inventory] Job %s crashed", job_id)
        update_inventory_job(job_id, "failed", "internal error")


def _snapshot_actor_pages(snapshot_key: str, page_size: int = 100):
    page = 1
    safe_page_size = max(1, min(int(page_size or 100), 500))
    while True:
        result = get_snapshot_actors(snapshot_key, page=page, page_size=safe_page_size)
        actors = result.get("data", [])
        if not actors:
            break
        yield actors
        if page >= int(result.get("total_pages") or page):
            break
        page += 1


async def _run_actor_auto_match(snapshot_key: str) -> dict:
    actor_mapping_result = {
        "enabled": config.actor_mapping_auto_match_after_collect,
        "checked": 0,
        "auto_confirmed": 0,
        "candidates_created": 0,
        "ambiguous": 0,
        "skipped": 0,
        "errors": [],
    }
    if config.actor_mapping_auto_match_after_collect:
        try:
            from services.actor_mapping_candidates import auto_match_actor_mappings

            actor_mapping_result = await auto_match_actor_mappings(snapshot_key=snapshot_key)
            actor_mapping_result["enabled"] = True
            logger.info(
                "[Inventory] Actor auto-match completed. "
                "Checked: %s, Confirmed: %s, Candidates: %s",
                actor_mapping_result.get("checked", 0),
                actor_mapping_result.get("auto_confirmed", 0),
                actor_mapping_result.get("candidates_created", 0),
            )
        except Exception as e:
            actor_mapping_result = {
                **actor_mapping_result,
                "enabled": True,
                "failed": True,
                "error": str(e),
            }
            logger.exception("[Inventory] Actor auto-match failed after collect")
    return actor_mapping_result


def _save_actors_videos(snapshot_key: str, actors_data: list[dict], *, upsert: bool = False) -> int:
    total_items = sum(len(actor.get("items", [])) for actor in actors_data)
    for actor in actors_data:
        for item in actor.get("items", []):
            save = upsert_emvy_snapshot if upsert else save_emvy_snapshot
            save(
                snapshot_key=snapshot_key,
                actress_id=actor["actress_id"],
                actress_name=actor["actress_name"],
                emby_item_id=item["item_id"],
                title=item.get("title", ""),
                filename=item.get("filename", ""),
            )
    return total_items


def _sync_inventory_actors(actors_data: list[dict]):
    for actor in actors_data:
        upsert_inventory_actor(actor["actress_id"], actor["actress_name"])


def _actors_with_snapshot_counts(snapshot_key: str, actors_data: list[dict]) -> list[dict]:
    merged = []
    for actor in actors_data:
        actor_with_count = dict(actor)
        actor_with_count["video_count"] = len(get_snapshot_videos(snapshot_key, actor["actress_id"]))
        merged.append(actor_with_count)
    return merged


async def _run_full_collect_job(job_id: int, emby) -> None:
    # 1. 生成新快照 key
    snapshot_key = create_snapshot_key()
    update_inventory_progress(job_id, 5)
    logger.info("[Inventory] Created snapshot key: %s", snapshot_key)

    # 2. 从 Emby 采集所有影片及演员
    actors_data, total = await emby.collect_all_movies_with_actors()
    update_inventory_progress(job_id, 30)
    logger.info("[Inventory] Collected %s actors, %s total movies", len(actors_data), total)

    # 3. 保存演员快照
    save_emby_actors_snapshot(snapshot_key, actors_data)
    update_inventory_progress(job_id, 40)

    # 4. 保存影片快照（每个演员的每部影片），报告进度
    total_items = sum(len(actor.get("items", [])) for actor in actors_data)
    processed = 0
    for actor in actors_data:
        for item in actor.get("items", []):
            save_emvy_snapshot(
                snapshot_key=snapshot_key,
                actress_id=actor["actress_id"],
                actress_name=actor["actress_name"],
                emby_item_id=item["item_id"],
                title=item.get("title", ""),
                filename=item.get("filename", ""),
            )
            processed += 1
            # 每处理10%报告一次进度
            if processed % max(1, total_items // 10) == 0:
                pct = 40 + int(50 * processed / max(total_items, 1))
                update_inventory_progress(job_id, min(pct, 89))

    # 5. 同步 inventory_actors 表
    _sync_inventory_actors(actors_data)
    actor_mapping_result = await _run_actor_auto_match(snapshot_key)

    update_inventory_progress(job_id, 95)
    # 更新作业，关联快照key
    update_inventory_job(
        job_id,
        "completed",
        snapshot_key=snapshot_key,
        result={
            "snapshot_key": snapshot_key,
            "mode": "full",
            "actors": len(actors_data),
            "videos": total,
            "actor_mapping": actor_mapping_result,
        },
    )
    update_inventory_progress(job_id, 100)
    logger.info("[Inventory] Collection job %s completed. Snapshot: %s", job_id, snapshot_key)


async def _reconcile_deleted_emby_items(
    emby,
    snapshot_key: str,
    actors_data: list[dict],
) -> tuple[int, set[int]]:
    """Drop snapshot rows whose Emby item no longer exists.

    Returns (deleted_row_count, set_of_actor_ids_with_changes).
    """
    try:
        live_ids = set(await emby.iter_item_ids())
    except Exception:
        logger.exception("[Inventory] Failed to fetch live Emby item ids; skipping delete sync")
        return 0, set()

    if not live_ids:
        # Treat an empty live list as "Emby probably broken" rather than
        # "everything is gone" — bail rather than wiping the snapshot.
        logger.warning("[Inventory] Emby returned no items; skipping delete sync")
        return 0, set()

    snapshot_ids = get_emby_item_ids_for_snapshot(snapshot_key)
    stale = [item_id for item_id in snapshot_ids if item_id not in live_ids]
    if not stale:
        return 0, set()

    deleted = delete_emby_snapshot_rows(snapshot_key, stale)
    affected_actor_ids = {actor["actress_id"] for actor in actors_data}
    logger.info(
        "[Inventory] Pruned %s stale snapshot rows (key=%s)",
        deleted,
        snapshot_key,
    )
    return deleted, affected_actor_ids


async def _run_incremental_collect_job(job_id: int, emby) -> None:
    previous_key = get_latest_snapshot_key()
    if not previous_key:
        logger.info("[Inventory] No existing snapshot, falling back to full collection")
        await _run_full_collect_job(job_id, emby)
        return

    since_iso = get_snapshot_created_at(previous_key)
    if not since_iso:
        logger.info("[Inventory] Snapshot %s has no timestamp, falling back to full collection", previous_key)
        await _run_full_collect_job(job_id, emby)
        return

    snapshot_key = clone_snapshot(previous_key)
    update_inventory_progress(job_id, 10)
    logger.info("[Inventory] Cloned snapshot %s to %s", previous_key, snapshot_key)

    actors_data, total = await emby.collect_incremental_movies_with_actors(since_iso=since_iso)
    update_inventory_progress(job_id, 40)
    logger.info(
        "[Inventory] Collected incremental delta: %s actors, %s movies since %s",
        len(actors_data),
        total,
        since_iso,
    )

    processed = _save_actors_videos(snapshot_key, actors_data, upsert=True)

    # Reconcile deletions: anything still in our cloned snapshot but missing
    # from Emby's current item-id roster has been removed upstream. Without
    # this step the snapshot grows monotonically and removed items get
    # silently counted as "still in the library" forever.
    deleted_count, removed_actor_ids = await _reconcile_deleted_emby_items(
        emby, snapshot_key, actors_data
    )

    save_emby_actors_snapshot(snapshot_key, _actors_with_snapshot_counts(snapshot_key, actors_data))
    _sync_inventory_actors(actors_data)
    update_inventory_progress(job_id, 90)

    actor_mapping_result = await _run_actor_auto_match(snapshot_key)
    # Bound table growth — old snapshot keys are no longer referenced once a
    # newer one exists, so dropping them is safe.
    pruned_keys = prune_old_snapshots(config.inventory_snapshot_retention)
    update_inventory_progress(job_id, 95)
    update_inventory_job(
        job_id,
        "completed",
        snapshot_key=snapshot_key,
        result={
            "snapshot_key": snapshot_key,
            "source_snapshot_key": previous_key,
            "mode": "incremental",
            "since": since_iso,
            "actors": len(actors_data),
            "videos": total,
            "upserted": processed,
            "deleted_from_snapshot": deleted_count,
            "pruned_snapshot_keys": pruned_keys,
            "actor_mapping": actor_mapping_result,
        },
    )
    update_inventory_progress(job_id, 100)
    logger.info("[Inventory] Incremental collection job %s completed. Snapshot: %s", job_id, snapshot_key)


async def run_collect_job(job_id: int, mode: str = "full"):
    """采集阶段：从 Emby 存快照。"""
    update_inventory_job(job_id, "running")
    normalized_mode = mode if mode in {"full", "incremental"} else "full"
    logger.info(
        "[Inventory] Starting collection job %s, mode: %s",
        job_id, normalized_mode,
    )

    try:
        emby = get_emby_client()
        if normalized_mode == "incremental":
            await _run_incremental_collect_job(job_id, emby)
        else:
            await _run_full_collect_job(job_id, emby)

    except Exception as e:
        logger.exception("[Inventory] Collection job %s failed", job_id)
        update_inventory_job(job_id, "failed", str(e))
        update_inventory_progress(job_id, 0)


async def run_compare_job(job_id: int, snapshot_key: Optional[str] = None):
    """对比阶段：基于快照数据对比 JavInfo，计算缺失（使用批量接口）"""
    update_inventory_job(job_id, "running")
    logger.info("[Inventory] Starting compare job %s, snapshot: %s", job_id, snapshot_key)

    try:
        if not snapshot_key:
            snapshot_key = get_latest_snapshot_key()

        if not snapshot_key:
            update_inventory_job(job_id, "failed", "No snapshot available. Please run collect first.")
            return

        exempt_set = _load_exempt_set()
        scanned = 0
        missing_total = 0
        unmapped = 0
        unmapped_actor_ids: list[int] = []
        failed = 0
        mapped = 0
        actor_total = 0
        pipeline = WatchlistPipeline()
        logger.info("[Inventory] Comparing actors from snapshot %s", snapshot_key)

        for actors in _snapshot_actor_pages(snapshot_key):
            actor_total += len(actors)

            # Phase 1 — resolve confirmed mappings (fast local DB lookups).
            pending: list[tuple[dict, int, str]] = []
            for actor in actors:
                emby_actor_id = actor["actress_id"]
                mapping = get_confirmed_actor_mapping(emby_actor_id)
                if not mapping:
                    unmapped += 1
                    unmapped_actor_ids.append(emby_actor_id)
                    # Intentionally do NOT zero out previous stats — they may
                    # have been computed when a mapping existed earlier, and
                    # writing 0/0 here would silently hide them. Leave the row
                    # untouched so the UI shows "unmapped" instead of "0".
                    continue
                pending.append((
                    actor,
                    mapping["javinfo_actress_id"],
                    mapping.get("javinfo_actress_name") or actor["actress_name"],
                ))

            if not pending:
                continue

            # Phase 2 — fetch JavInfo filmographies concurrently (bounded), so a
            # page of mapped actors costs ~max(latency) instead of sum(latency).
            sem = asyncio.Semaphore(8)

            async def _bounded_fetch(jid: int):
                async with sem:
                    return await pipeline.fetch_actress_videos(jid)

            fetched = await asyncio.gather(
                *(_bounded_fetch(jid) for _, jid, _ in pending),
                return_exceptions=True,
            )

            # Phase 3 — reconcile each actor sequentially (ordered DB writes).
            for (actor, javinfo_actress_id, javinfo_actress_name), javinfo_videos in zip(pending, fetched):
                emby_actor_id = actor["actress_id"]

                if isinstance(javinfo_videos, Exception):
                    logger.error(
                        "[Inventory] Fetch failed for mapped actor %s->%s",
                        emby_actor_id,
                        javinfo_actress_id,
                        exc_info=javinfo_videos,
                    )
                    update_inventory_actor_stats(emby_actor_id, -1, -1)
                    failed += 1
                    continue

                if not javinfo_videos:
                    update_inventory_actor_stats(emby_actor_id, -1, -1)
                    failed += 1
                    continue

                mapped += 1
                snapshot_videos = get_snapshot_videos(snapshot_key, emby_actor_id)
                total = 0
                missing = 0

                for video in javinfo_videos:
                    content_id = (video.get("content_id") or video.get("dvd_id") or "").upper()
                    code = video_code(video).upper()
                    if not content_id and not code:
                        continue

                    total += 1
                    scanned += 1

                    if content_id in exempt_set or code in exempt_set:
                        continue

                    matched = video_in_snapshot_match(video, snapshot_videos)

                    if matched is None:
                        add_missing_video(
                            content_id=_video_content_id(video),
                            actress_id=emby_actor_id,
                            title=_video_title(video),
                            release_date=video.get("release_date"),
                            jacket_thumb_url=video.get("jacket_thumb_url"),
                        )
                        from database import upsert_candidate_from_video
                        upsert_candidate_from_video(
                            video=video,
                            actress_id=javinfo_actress_id,
                            actress_name=javinfo_actress_name,
                            source="inventory",
                            reason=f"inventory_compare:{snapshot_key}",
                            provenance=_missing_provenance(snapshot_key),
                        )
                        missing += 1
                        missing_total += 1
                    else:
                        _record_owned_video(video, emby_actor_id, matched)
                        delete_key = video.get("content_id") or video.get("dvd_id") or code
                        if delete_key:
                            from database import delete_missing_video
                            delete_missing_video(delete_key)

                update_inventory_actor_stats(emby_actor_id, total, missing)

        result = {
            "snapshot_key": snapshot_key,
            "actors": actor_total,
            "mapped": mapped,
            "unmapped": unmapped,
            # First 500 unmapped actor IDs — enough to drive a "fix mappings"
            # CTA in the UI without bloating the job result blob.
            "unmapped_actor_ids": unmapped_actor_ids[:500],
            "failed": failed,
            "scanned": scanned,
            "missing": missing_total,
            "candidates": missing_total,
        }
        update_inventory_job(job_id, "completed", error_msg=f"unmapped={unmapped}; missing={missing_total}", result=result)
        logger.info(
            "[Inventory] Compare job %s completed. Scanned: %s, Missing: %s, Unmapped: %s",
            job_id,
            scanned,
            missing_total,
            unmapped,
        )

    except Exception as e:
        logger.exception("[Inventory] Compare job %s failed", job_id)
        update_inventory_job(job_id, "failed", str(e))


async def run_actor_compare_job(job_id: int, actress_id: int, snapshot_key: Optional[str] = None):
    """单演员增量对比"""
    update_inventory_job(job_id, "running")
    logger.info("[Inventory] Starting actor compare job %s for actress %s", job_id, actress_id)

    try:
        if not snapshot_key:
            snapshot_key = get_latest_snapshot_key()

        if not snapshot_key:
            update_inventory_job(job_id, "failed", "No snapshot available")
            return

        mapping = get_confirmed_actor_mapping(actress_id)
        if not mapping:
            # Preserve prior stats — see ``run_compare_job`` for why we no
            # longer overwrite with 0/0 on unmapped.
            update_inventory_job(
                job_id,
                "completed",
                "unmapped=1; missing=0",
                result={
                    "snapshot_key": snapshot_key,
                    "actors": 1,
                    "mapped": 0,
                    "unmapped": 1,
                    "unmapped_actor_ids": [actress_id],
                    "failed": 0,
                    "scanned": 0,
                    "missing": 0,
                    "candidates": 0,
                },
            )
            logger.info("[Inventory] Actor compare skipped unmapped Emby actor %s", actress_id)
            return

        pipeline = WatchlistPipeline()
        javinfo_actress_id = mapping["javinfo_actress_id"]
        javinfo_actress_name = mapping.get("javinfo_actress_name") or ""

        # 查 JavInfo
        javinfo_videos = await pipeline.fetch_actress_videos(javinfo_actress_id)

        # 查 Emby 快照
        snapshot_videos = get_snapshot_videos(snapshot_key, actress_id)
        exempt_set = _load_exempt_set()

        total = len(javinfo_videos)
        missing = 0

        for video in javinfo_videos:
            content_id = (video.get("content_id") or video.get("dvd_id") or "").upper()
            if not content_id:
                continue

            if content_id in exempt_set:
                continue

            matched = video_in_snapshot_match(video, snapshot_videos)

            if matched is None:
                add_missing_video(
                    content_id=_video_content_id(video),
                    actress_id=actress_id,
                    title=_video_title(video),
                    release_date=video.get("release_date"),
                    jacket_thumb_url=video.get("jacket_thumb_url"),
                )
                from database import upsert_candidate_from_video
                upsert_candidate_from_video(
                    video=video,
                    actress_id=javinfo_actress_id,
                    actress_name=javinfo_actress_name,
                    source="inventory",
                    reason=f"inventory_actor_compare:{snapshot_key}",
                    provenance=_missing_provenance(snapshot_key),
                )
                missing += 1
            else:
                _record_owned_video(video, actress_id, matched)
                from database import delete_missing_video
                delete_missing_video(video.get("content_id") or video.get("dvd_id") or content_id)

        update_inventory_actor_stats(actress_id, total, missing)
        update_inventory_job(
            job_id,
            "completed",
            result={
                "snapshot_key": snapshot_key,
                "actors": 1,
                "mapped": 1,
                "unmapped": 0,
                "failed": 0,
                "scanned": total,
                "missing": missing,
                "candidates": missing,
            },
        )
        logger.info(
            "[Inventory] Actor compare job %s completed. Total: %s, Missing: %s",
            job_id,
            total,
            missing,
        )

    except Exception as e:
        logger.exception("[Inventory] Actor compare job %s failed", job_id)
        update_inventory_job(job_id, "failed", str(e))


# === 定时任务入口（保留兼容）===

async def run_inventory_comparison(job_type: str = "full", actor_id: int | None = None):
    """定时任务入口（创建作业并执行）"""
    snapshot_key = get_latest_snapshot_key() if job_type != "collect" else None
    job_id = add_inventory_job(job_type, actor_id, snapshot_key)
    if job_type == "collect":
        await run_collect_job(job_id)
    elif job_type == "full":
        await run_compare_job(job_id, snapshot_key)
    else:
        await run_actor_compare_job(job_id, actor_id, snapshot_key)
