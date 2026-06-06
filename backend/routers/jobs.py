"""Global background jobs API."""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import cancel_job, get_job, list_jobs

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("")
def list_job_rows(
    kind: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    return {"data": list_jobs(kind=_clean(kind), status=_clean(status), limit=limit)}


@router.get("/stream")
def stream_jobs(
    kind: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    poll_seconds: float = 1.0,
) -> StreamingResponse:
    return StreamingResponse(
        _job_event_stream(
            kind=_clean(kind),
            status=_clean(status),
            limit=_limit(limit),
            poll_seconds=poll_seconds,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{job_id}")
def get_job_row(job_id: int) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.post("/{job_id}/cancel")
def cancel_job_row(job_id: int) -> dict[str, Any]:
    canceled = cancel_job(job_id)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if not canceled and job.get("status") != "canceled":
        return job
    return job


async def _job_event_stream(
    *,
    kind: str | None,
    status: str | None,
    limit: int,
    poll_seconds: float,
) -> AsyncIterator[bytes]:
    seen: dict[int, tuple[Any, ...]] = {}
    interval = max(0.1, float(poll_seconds or 1.0))
    while True:
        rows = await asyncio.to_thread(list_jobs, kind=kind, status=status, limit=limit)
        emitted = False
        for job in rows:
            job_id = int(job["id"])
            fingerprint = _job_fingerprint(job)
            if seen.get(job_id) == fingerprint:
                continue
            seen[job_id] = fingerprint
            emitted = True
            yield f"data: {_json(job)}\n\n".encode("utf-8")
        if not emitted:
            yield b": keep-alive\n\n"
        await asyncio.sleep(interval)


def _job_fingerprint(job: dict[str, Any]) -> tuple[Any, ...]:
    return (
        job.get("status"),
        job.get("progress"),
        _jsonable_datetime(job.get("finished_at")),
    )


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=_jsonable_datetime)


def _jsonable_datetime(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _clean(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _limit(value: Any) -> int:
    try:
        return max(1, min(int(value), 500))
    except (TypeError, ValueError):
        return 50
