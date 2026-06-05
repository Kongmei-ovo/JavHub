"""End-to-end supplement pipeline.

Chains the previously-separate stages into one runnable, observable flow:

    collect (Emby snapshot) → compare (vs JavInfo → candidates) → enrich/download

Each stage still delegates to its existing, tested entrypoint; this module only
sequences them on the shared background loop and records a single roll-up result
on a tracking inventory job. Stage 3 defaults to a dry run (preview) so callers
opt in explicitly before anything is sent to a downloader.
"""
from __future__ import annotations

import logging

from config import config
from database import (
    add_inventory_job,
    get_inventory_job,
    get_latest_snapshot_key,
    update_inventory_job,
    update_inventory_progress,
)
from scheduler.inventory_tasks import (
    run_actor_compare_job,
    run_collect_job,
    run_compare_job,
)
from services.candidate_processor import preview_candidates, process_candidates

logger = logging.getLogger(__name__)


def _job_view(job_id: int) -> dict:
    job = get_inventory_job(job_id) or {}
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "result": job.get("result"),
        "error": job.get("error_msg"),
    }


async def run_supplement_pipeline(
    job_id: int,
    *,
    do_collect: bool = True,
    actor_id: int | None = None,
    process: bool = True,
    dry_run: bool = True,
    policy: str | None = None,
) -> dict:
    """Run the full supplement chain, updating ``job_id`` as it progresses.

    - ``do_collect``: refresh the Emby snapshot first (otherwise reuse latest).
    - ``actor_id``: restrict the compare stage to one Emby actor (else full).
    - ``process``: run the candidate stage. ``dry_run`` previews without sending.
    - ``policy``: candidate automation policy override (default: configured).
    """
    update_inventory_job(job_id, "running")
    summary: dict = {"stages": {}, "dry_run": dry_run, "actor_id": actor_id}

    try:
        # --- Stage 1: collect -------------------------------------------------
        if do_collect:
            collect_job = add_inventory_job("collect", None, None)
            await run_collect_job(collect_job)
            collected = get_inventory_job(collect_job) or {}
            snapshot_key = collected.get("snapshot_key") or get_latest_snapshot_key()
            summary["stages"]["collect"] = _job_view(collect_job)
            if collected.get("status") != "completed":
                update_inventory_job(job_id, "failed", "collect stage failed", result=summary)
                return summary
        else:
            snapshot_key = get_latest_snapshot_key()
            summary["stages"]["collect"] = {"skipped": True, "snapshot_key": snapshot_key}
        update_inventory_progress(job_id, 40)

        if not snapshot_key:
            update_inventory_job(job_id, "failed", "No snapshot available. Run collect first.", result=summary)
            return summary

        # --- Stage 2: compare -------------------------------------------------
        if actor_id is not None:
            compare_job = add_inventory_job("actor", actor_id, snapshot_key)
            await run_actor_compare_job(compare_job, actor_id, snapshot_key)
        else:
            compare_job = add_inventory_job("full", None, snapshot_key)
            await run_compare_job(compare_job, snapshot_key)
        compared = get_inventory_job(compare_job) or {}
        summary["stages"]["compare"] = _job_view(compare_job)
        update_inventory_progress(job_id, 75)
        if compared.get("status") != "completed":
            update_inventory_job(job_id, "failed", "compare stage failed", result=summary)
            return summary

        # --- Stage 3: enrich / download --------------------------------------
        if process:
            if dry_run:
                summary["stages"]["process"] = await preview_candidates(
                    filters={"status": "candidate"},
                    policy=policy,
                )
            else:
                summary["stages"]["process"] = await process_candidates(
                    filters={"status": "candidate"},
                    policy=policy or config.automation_download_policy,
                    operator="pipeline",
                )
        else:
            summary["stages"]["process"] = {"skipped": True}

        update_inventory_job(job_id, "completed", result=summary)
        update_inventory_progress(job_id, 100)
        logger.info("[Pipeline] supplement pipeline %s completed (dry_run=%s)", job_id, dry_run)
        return summary

    except Exception as exc:  # noqa: BLE001 - record and surface on the job row
        logger.exception("[Pipeline] supplement pipeline %s failed", job_id)
        update_inventory_job(job_id, "failed", str(exc), result=summary)
        return summary
