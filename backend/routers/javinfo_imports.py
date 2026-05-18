from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from config import config
from services import cache
from services.javinfo_import import (
    JavInfoImportConflict,
    JavInfoImportError,
    get_import_manager,
)

router = APIRouter(prefix="/api/v1/javinfo/imports", tags=["javinfo-imports"])


def _settings_from_body(body: dict[str, Any] | None) -> dict[str, Any]:
    body = body or {}
    incoming = body.get("import_db") if isinstance(body.get("import_db"), dict) else body.get("settings")
    incoming = incoming if isinstance(incoming, dict) else {}
    return config._merge_config(config.javinfo_import_db, incoming)


@router.post("/preflight")
async def preflight_import(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    expected_size = int(body.get("expected_size") or body.get("file_size") or 0)
    return await get_import_manager().preflight(_settings_from_body(body), expected_size=expected_size)


@router.post("/jobs")
async def create_import_job(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    filename = str(body.get("filename") or "").strip()
    if not filename:
        raise HTTPException(400, "filename is required")
    confirm_replace = bool(body.get("confirm_replace"))
    try:
        return get_import_manager().create_job(
            _settings_from_body(body),
            filename=filename,
            file_size=int(body.get("file_size") or 0),
            confirm_replace=confirm_replace,
        )
    except JavInfoImportConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/jobs/{job_id}/upload")
async def upload_import_dump(job_id: int, request: Request) -> dict[str, Any]:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/octet-stream":
        raise HTTPException(415, "upload must use application/octet-stream")
    manager = get_import_manager()
    try:
        job = await manager.save_upload(job_id, request.stream())
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, JavInfoImportError) as exc:
        raise HTTPException(400, str(exc)) from exc
    asyncio.create_task(_restore_after_upload(manager, job_id))
    return job


async def _restore_after_upload(manager, job_id: int) -> None:
    job = await manager.restore_job(job_id)
    if job.get("status") == "completed":
        cache.purge_all()


@router.get("/jobs")
async def list_import_jobs(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    return {"data": get_import_manager().list_jobs(limit=limit)}


@router.get("/jobs/{job_id}")
async def get_import_job(job_id: int) -> dict[str, Any]:
    job = get_import_manager().get_job(job_id)
    if not job:
        raise HTTPException(404, "import job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_import_job(job_id: int) -> dict[str, Any]:
    try:
        return await get_import_manager().cancel_job(job_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
