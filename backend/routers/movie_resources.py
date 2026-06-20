from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from config import config
from database import (
    delete_movie_resource,
    delete_all_movie_resources,
    list_movie_resources,
    set_default_movie_resource,
)
from services.canonical_resolver import resolve_canonical_code
from services.open115 import open115_client
from services.open115_downloader import open115_downloader

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


@router.delete("/{movie_id}/library")
async def delete_movie_library(movie_id: str):
    """Remove a whole film from the library: delete its entire 115 folder
    (one 番号 = one folder) and purge its ``movie_resources`` rows.

    Resolves the canonical 番号 so callers may pass any product content_id or a
    番号; falls back to the legacy product key when resources were registered
    under a content_id before the canonical cutover. This is an explicit,
    user-initiated destructive action, so the 115 folder is removed regardless
    of ``open115_delete_on_remove`` (which only gates incidental cleanup).
    """
    requested = str(movie_id or "").strip()
    if not requested:
        raise HTTPException(status_code=400, detail="movie_id 不能为空")
    canonical = resolve_canonical_code(requested)
    # Prefer the canonical key; fall back to the raw key for legacy downloads.
    key = canonical if list_movie_resources(canonical) else requested

    purged = delete_all_movie_resources(key)
    folder_deleted = False
    try:
        await open115_downloader.delete_movie_directory(key)
        folder_deleted = True
    except Exception:
        logger.exception("Failed to delete 115 folder for movie %s", key)

    return {
        "status": "ok",
        "movie_id": key,
        "purged_resources": len(purged),
        "folder_deleted": folder_deleted,
    }
