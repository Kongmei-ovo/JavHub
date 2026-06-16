from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from config import config
from database import (
    delete_movie_resource,
    list_movie_resources,
    set_default_movie_resource,
)
from services.open115 import open115_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/movies", tags=["movie-resources"])


@router.get("/{movie_id}/resources")
async def get_resources(movie_id: str):
    items = list_movie_resources(movie_id)
    return {"items": items, "total": len(items)}


@router.post("/{movie_id}/resources/{resource_id}/default")
async def set_default_resource(movie_id: str, resource_id: int):
    if not set_default_movie_resource(movie_id, resource_id):
        raise HTTPException(status_code=404, detail="可播放资源不存在")
    return {"status": "ok", "resource_id": resource_id}


@router.delete("/{movie_id}/resources/{resource_id}")
async def remove_resource(movie_id: str, resource_id: int):
    deleted = delete_movie_resource(movie_id, resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="资源不存在")
    if (
        str(deleted.get("provider") or "").strip().lower() == "open115"
        and str(deleted.get("remote_file_id") or "").strip()
        and config.open115_delete_on_remove
    ):
        try:
            await open115_client.delete_files(
                [str(deleted["remote_file_id"])],
                parent_id=deleted.get("parent_id"),
            )
        except Exception:
            logger.exception("Failed to delete 115 file for removed resource %s", resource_id)
    return {"status": "ok"}
