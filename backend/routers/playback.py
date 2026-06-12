"""播放链路端点：实时换链 + 播放进度 + 继续观看。

本路由响应一律不进响应缓存（直链有时效）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import (
    get_library_files_by_content_id,
    get_progress,
    list_continue_watching,
    save_progress,
)
from services.storage_resolver import get_resolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/playback", tags=["playback"])

VALID_SOURCES = ("library", "online")


def _public_file(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "path": row.get("path"),
        "size": row.get("size"),
        "backend": row.get("backend"),
        "modified_at": row.get("modified_at"),
    }


@router.get("/library/{content_id}")
async def library_play(content_id: str, file_id: Optional[int] = Query(None)) -> dict[str, Any]:
    """换链播放入口。直链实时获取，永不缓存/落库。"""
    files = get_library_files_by_content_id(content_id)
    if not files:
        raise HTTPException(status_code=404, detail={"message": "番号不在云盘库中"})
    chosen = files[0]
    if file_id is not None:
        chosen = next((f for f in files if f["id"] == file_id), None)
        if chosen is None:
            raise HTTPException(status_code=404, detail={"message": "指定文件不存在或已删除"})
    try:
        resolver = get_resolver(chosen["backend"])
        link = await resolver.resolve_play_url(chosen)
    except KeyError:
        raise HTTPException(status_code=500, detail={"message": f"不支持的存储后端: {chosen['backend']}"})
    except Exception as exc:
        logger.error("resolve play url failed for %s: %s", content_id, type(exc).__name__)
        raise HTTPException(status_code=502, detail={"message": "换链失败，请稍后重试"})

    progress = get_progress(content_id, source="library")
    return {
        "file": _public_file(chosen),
        "files": [_public_file(f) for f in files],
        "play": {"url": link.url, "kind": link.kind, "headers": link.headers},
        "progress": {
            "position_seconds": progress["position_seconds"] if progress else 0,
            "duration_seconds": progress["duration_seconds"] if progress else 0,
            "completed": bool(progress and progress.get("completed")),
        },
    }


class ProgressRequest(BaseModel):
    source: str = "library"
    position_seconds: float
    duration_seconds: float = 0


@router.put("/progress/{content_id}")
async def put_progress(content_id: str, req: ProgressRequest):
    if req.source not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail="source 必须是 library 或 online")
    return save_progress(content_id, req.source, req.position_seconds, req.duration_seconds)


@router.get("/progress/{content_id}")
async def read_progress(content_id: str, source: Optional[str] = Query(None)):
    progress = get_progress(content_id, source=source)
    if not progress:
        return {"content_id": content_id, "position_seconds": 0, "duration_seconds": 0, "completed": 0}
    return progress


@router.get("/continue")
async def continue_watching(limit: int = Query(12, ge=1, le=50)):
    """继续观看：进度行 + 元数据（标题/封面）懒加载合并。"""
    rows = list_continue_watching(limit)
    if not rows:
        return {"items": []}

    from modules.info_client import get_info_client

    client = get_info_client()

    async def enrich(row: dict) -> dict:
        item = {
            "content_id": row["content_id"],
            "source": row["source"],
            "position_seconds": row["position_seconds"],
            "duration_seconds": row["duration_seconds"],
            "updated_at": row.get("updated_at"),
            "video": None,
        }
        try:
            item["video"] = await client.get_video(row["content_id"])
        except Exception:
            pass  # 元数据缺失不阻断列表
        return item

    items = await asyncio.gather(*(enrich(r) for r in rows))
    return {"items": list(items)}
