"""Inventory job and pipeline routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import add_inventory_job, get_inventory_job, get_inventory_jobs


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class TriggerJobRequest(BaseModel):
    job_type: str
    actor_id: Optional[int] = None
    snapshot_key: Optional[str] = None
    mode: str = "full"


@router.post("/jobs/trigger")
def trigger_job(req: TriggerJobRequest):
    """Trigger an inventory job."""
    job_id = add_inventory_job(req.job_type, req.actor_id, req.snapshot_key)
    from scheduler.inventory_tasks import run_inventory_job

    run_inventory_job(job_id, mode=req.mode if req.job_type == "collect" else "full")
    return {"job_id": job_id, "status": "pending"}


class PipelineRequest(BaseModel):
    do_collect: bool = True
    actor_id: Optional[int] = None
    process: bool = True
    dry_run: bool = True
    policy: Optional[str] = None


@router.post("/pipeline/run")
def run_pipeline(req: PipelineRequest):
    """Run the collect -> compare -> enrich/download supplement pipeline."""
    job_id = add_inventory_job("supplement", req.actor_id, None)
    from scheduler.worker_loop import submit
    from services.supplement_pipeline import run_supplement_pipeline

    submit(
        run_supplement_pipeline(
            job_id,
            do_collect=req.do_collect,
            actor_id=req.actor_id,
            process=req.process,
            dry_run=req.dry_run,
            policy=req.policy,
        ),
        kind="supplement",
        label=f"Supplement pipeline {job_id}",
    )
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs")
def list_jobs():
    """List inventory job history."""
    return {"data": get_inventory_jobs()}


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    """Get one inventory job."""
    job = get_inventory_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
