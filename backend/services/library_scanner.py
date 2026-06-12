"""云盘文件索引扫描器。

全量：递归遍历 config.library_root_paths，收集视频文件，提取番号入库。
增量：只扫指定目录（下载完成回调 / 手动单目录刷新）。

匹配策略：文件名 extract_code 失败时回退父目录名（CMS/qB 常以番号建目录）。
匹配只看番号形态，不在线验证元数据存在性——展示/播放时经 info_client 懒加载。
manual / ignored 状态的行永不被自动扫描覆盖（database 层保证）。
"""
from __future__ import annotations

import asyncio
import logging
import posixpath
import time

from config import config
from database import (
    create_scan_run,
    is_scan_running,
    mark_files_deleted,
    update_scan_run,
    upsert_library_file,
)
from modules.code_matcher import extract_code
from services.openlist import OpenListFsError, openlist_client

logger = logging.getLogger(__name__)

SCAN_DIR_CONCURRENCY = 3
MAX_SCAN_DEPTH = 8


def _is_video(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.endswith(ext) for ext in config.library_video_exts)


def _match_code(name: str, parent_dir: str) -> str | None:
    """文件名优先，父目录名兜底。返回展示形番号（ABC-123）。"""
    code = extract_code(name)
    if code:
        return code
    parent_name = posixpath.basename(parent_dir.rstrip("/"))
    return extract_code(parent_name)


class LibraryScanner:
    def __init__(self, client=None):
        self.client = client or openlist_client
        self.backend = config.library_backend

    async def _walk(self, root: str, stats: dict, seen_paths: set[str], depth: int = 0) -> None:
        if depth > MAX_SCAN_DEPTH:
            logger.warning("library scan: max depth reached at %s", root)
            return
        try:
            entries = await self.client.fs_list(root)
        except OpenListFsError as exc:
            # 单目录失败：记日志跳过，不中止整个扫描
            logger.error("library scan: %s", exc)
            stats["errors"] += 1
            return
        interval = config.library_scan_interval_ms / 1000.0
        subdirs = []
        for entry in entries:
            if entry.is_dir:
                subdirs.append(entry.path)
                continue
            if not _is_video(entry.name):
                continue
            stats["seen"] += 1
            seen_paths.add(entry.path)
            code = _match_code(entry.name, root)
            _, created = upsert_library_file(
                backend=self.backend,
                path=entry.path,
                name=entry.name,
                size=entry.size,
                modified_at=entry.modified,
                content_id=code,
                match_status="matched" if code else "unmatched",
            )
            if created:
                stats["added"] += 1
            if code:
                stats["matched"] += 1
        for subdir in subdirs:
            if interval > 0:
                await asyncio.sleep(interval)
            await self._walk(subdir, stats, seen_paths, depth + 1)

    async def scan(self, mode: str = "full", paths: list[str] | None = None) -> dict:
        """执行扫描。mode=full 递归全部 root_paths 并对消失文件打软删除；
        mode=incremental 只扫 paths（或 root_paths），不做全库软删除。
        """
        roots = paths or config.library_root_paths
        if not roots:
            raise ValueError("library.root_paths is empty")
        run_id = create_scan_run(mode, root_path=",".join(roots))
        stats = {"seen": 0, "added": 0, "matched": 0, "removed": 0, "errors": 0}
        started = time.monotonic()
        try:
            seen_paths: set[str] = set()
            for root in roots:
                await self._walk(root, stats, seen_paths)
            if mode == "full":
                stats["removed"] = mark_files_deleted(self.backend, seen_paths)
            else:
                for root in roots:
                    stats["removed"] += mark_files_deleted(self.backend, seen_paths, prefix=root)
            update_scan_run(
                run_id,
                status="done",
                files_seen=stats["seen"],
                files_added=stats["added"],
                files_removed=stats["removed"],
                files_matched=stats["matched"],
            )
            logger.info(
                "library scan %s done in %.1fs: seen=%d matched=%d removed=%d errors=%d",
                mode, time.monotonic() - started,
                stats["seen"], stats["matched"], stats["removed"], stats["errors"],
            )
            return {"run_id": run_id, **stats}
        except Exception as exc:
            update_scan_run(run_id, status="failed", error=str(exc)[:500])
            logger.exception("library scan %s failed", mode)
            raise


async def run_scan(mode: str = "full", paths: list[str] | None = None) -> dict:
    if is_scan_running():
        raise RuntimeError("已有扫描任务在运行")
    return await LibraryScanner().scan(mode=mode, paths=paths)


# ── 下载完成 → 增量扫描（带防抖）────────────────────────────────

_recent_incremental: dict[str, float] = {}
INCREMENTAL_DEBOUNCE_SECONDS = 300


async def trigger_incremental_scan(path: str) -> bool:
    """下载完成回调入口。同目录 5 分钟内只触发一次。失败只记日志不上抛。"""
    if not config.library_enabled:
        return False
    now = time.monotonic()
    last = _recent_incremental.get(path)
    if last is not None and now - last < INCREMENTAL_DEBOUNCE_SECONDS:
        return False
    _recent_incremental[path] = now
    try:
        await run_scan(mode="incremental", paths=[path])
        return True
    except Exception as exc:
        logger.error("incremental library scan failed for %s: %s", path, exc)
        return False
