from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from scheduler.tasks import (
    MANUAL_JOB_IDS,
    get_scheduler_job_result,
    scheduler,
    trigger_scheduler_job,
)

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


@router.post("/jobs/{job_id}/run")
def run_scheduler_job(job_id: str) -> dict[str, Any]:
    """立即触发一个调度作业（仅限白名单）。"""
    try:
        return trigger_scheduler_job(job_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"未知或不可手动触发的调度作业: {job_id}（可用: {', '.join(MANUAL_JOB_IDS)}）",
        )
