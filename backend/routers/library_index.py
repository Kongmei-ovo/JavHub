"""云盘文件索引管理端点。

约束：content_id 是对外稳定 Id 的唯一来源；本路由不输出任何直链。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import config
from database import (
    get_latest_scan_run,
    get_library_file,
    ignore_file,
    is_scan_running,
    library_summary,
    list_library_files_page,
    set_file_match,
)
from modules.code_matcher import extract_code, normalize_code
from services.library_scanner import run_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/library", tags=["library"])


class ScanRequest(BaseModel):
    mode: str = "full"
    paths: Optional[list[str]] = None


class MatchRequest(BaseModel):
    content_id: str


@router.post("/scan")
async def trigger_scan(req: ScanRequest):
    if not config.library_enabled:
        raise HTTPException(status_code=400, detail="library 功能未启用")
    if req.mode not in ("full", "incremental"):
        raise HTTPException(status_code=400, detail="mode 必须是 full 或 incremental")
    if is_scan_running():
        raise HTTPException(status_code=409, detail="已有扫描任务在运行")

    async def _run():
        try:
            await run_scan(mode=req.mode, paths=req.paths)
        except Exception:
            logger.exception("library scan task failed")

    asyncio.create_task(_run())
    return {"status": "started", "mode": req.mode}


@router.get("/scan/status")
async def scan_status():
    run = get_latest_scan_run()
    return {"running": is_scan_running(), "latest": run}


@router.get("/summary")
async def summary():
    return library_summary()


@router.get("/files")
async def list_files(
    status: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    if content_id:
        from database import get_library_files_by_content_id

        files = get_library_files_by_content_id(content_id)
        return {"items": files, "total": len(files), "page": 1, "page_size": len(files) or 1}
    rows, total = list_library_files_page(
        status=status, search=search, page=page, page_size=page_size
    )
    # 给未匹配行附带番号猜测，前端预填
    for row in rows:
        if row.get("match_status") == "unmatched":
            row["guessed_code"] = extract_code(row.get("name") or "")
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.post("/files/{file_id}/match")
async def match_file(file_id: int, req: MatchRequest):
    code = (req.content_id or "").strip()
    if not normalize_code(code):
        raise HTTPException(status_code=400, detail="content_id 不合法")
    if not get_library_file(file_id):
        raise HTTPException(status_code=404, detail="文件不存在")
    # 校验元数据存在（不存在只警告不阻断——元数据库可能尚未补全该番号）
    metadata_found = True
    try:
        from modules.info_client import get_info_client

        await get_info_client().get_video(code)
    except Exception:
        metadata_found = False
    set_file_match(file_id, code.upper(), status="manual")
    return {"status": "ok", "content_id": code.upper(), "metadata_found": metadata_found}


@router.post("/files/{file_id}/ignore")
async def ignore_library_file(file_id: int):
    if not ignore_file(file_id):
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"status": "ok"}


@router.get("/baseline-diff")
async def baseline_diff(
    emby_key: Optional[str] = Query(None, description="Emby 快照 key，缺省取最新"),
    library_key: str = Query(..., description="library 快照 key（先用 baseline=library 跑一次 collect 获得）"),
):
    """切换 inventory.baseline 前的人工核对：对比两个快照的番号差异。"""
    from database import get_latest_snapshot_key
    from services.library_snapshot import diff_library_vs_emby

    resolved_emby_key = emby_key or get_latest_snapshot_key()
    if not resolved_emby_key:
        raise HTTPException(status_code=404, detail="没有可用的 Emby 快照")
    return await diff_library_vs_emby(resolved_emby_key, library_key)
