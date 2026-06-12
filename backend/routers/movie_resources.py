from __future__ import annotations

from fastapi import APIRouter, HTTPException

from database import (
    delete_movie_resource,
    list_movie_resources,
    set_default_movie_resource,
)

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
    if not delete_movie_resource(movie_id, resource_id):
        raise HTTPException(status_code=404, detail="资源不存在")
    return {"status": "ok"}
