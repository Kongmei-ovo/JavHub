from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from scheduler.tasks import get_scheduler_job_result, scheduler

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@router.get("/jobs")
def scheduler_jobs() -> list[dict[str, Any]]:
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": _isoformat(getattr(job, "next_run_time", None)),
            **get_scheduler_job_result(job.id),
        }
        for job in scheduler.get_jobs()
    ]
