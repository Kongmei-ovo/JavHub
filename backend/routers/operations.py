"""Operations overview API for the inventory workflow."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from config import config
from database import (
    download_candidate_stats,
    get_all_missing_videos,
    get_inventory_jobs,
    get_latest_snapshot_key,
    get_snapshot_actors,
    list_candidate_process_runs,
    list_download_candidates,
    mapping_summary,
)

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/overview")
async def operations_overview() -> dict[str, Any]:
    snapshot_key = get_latest_snapshot_key()
    snapshot_actors = get_snapshot_actors(snapshot_key, page_size=100000).get("data", []) if snapshot_key else []
    candidate_stats = download_candidate_stats()
    jobs = get_inventory_jobs(limit=10)
    missing = get_all_missing_videos()

    supplement: dict[str, Any] = {"available": False}
    try:
        from modules.info_client import get_info_client

        client = get_info_client()
        stats = await client.proxy_get("/api/v1/supplement/stats", params=None)
        queued = await client.proxy_get(
            "/api/v1/supplement/jobs",
            params={"page": 1, "page_size": 1, "status": "queued"},
        )
        running = await client.proxy_get(
            "/api/v1/supplement/jobs",
            params={"page": 1, "page_size": 1, "status": "running"},
        )
        failed = await client.proxy_get(
            "/api/v1/supplement/jobs",
            params={"page": 1, "page_size": 1, "status": "failed"},
        )
        supplement = {
            "available": True,
            "stats": stats,
            "queued": _total_from_response(queued),
            "running": _total_from_response(running),
            "failed": _total_from_response(failed),
        }
    except Exception as exc:
        supplement = {"available": False, "error": str(exc)}

    candidate_rows = list_download_candidates(status="candidate", limit=100000)
    ready_candidates = sum(1 for row in candidate_rows if row.get("magnet"))

    return {
        "status": "ok",
        "automation": config.automation,
        "snapshot": {
            "snapshot_key": snapshot_key,
            "actor_count": len(snapshot_actors),
        },
        "mapping": {
            **mapping_summary(snapshot_actors),
            "auto_match": config.actor_mapping,
        },
        "missing": {
            "total": len(missing),
            "top_actresses": _top_missing_actresses(missing),
        },
        "candidates": {
            **candidate_stats,
            "ready": ready_candidates,
        },
        "candidate_runs": {
            "recent": list_candidate_process_runs(limit=5),
            "schedule": _candidate_schedule_state(),
        },
        "inventory_jobs": {
            "recent": jobs,
            "running": sum(1 for job in jobs if job.get("status") == "running"),
            "failed": sum(1 for job in jobs if job.get("status") == "failed"),
        },
        "supplement": supplement,
    }


@router.post("/candidate-processing/run")
async def run_candidate_processing_now() -> dict[str, Any]:
    from services.candidate_processor import run_automatic_candidate_processing

    return await run_automatic_candidate_processing(operator="manual")


def _top_missing_actresses(rows: list[dict], limit: int = 8) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        key = str(row.get("actress_id") or "")
        if not key:
            continue
        item = grouped.setdefault(
            key,
            {
                "actress_id": row.get("actress_id"),
                "actress_name": row.get("actress_name") or "",
                "missing_count": 0,
            },
        )
        item["missing_count"] += 1
    return sorted(grouped.values(), key=lambda item: item["missing_count"], reverse=True)[:limit]


def _total_from_response(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(value.get("total") or value.get("total_count") or 0)


def _candidate_schedule_state() -> dict[str, Any]:
    try:
        from scheduler.tasks import candidate_auto_process_schedule_state

        return candidate_auto_process_schedule_state()
    except Exception as exc:
        return {
            "enabled": False,
            "running": False,
            "next_run_time": None,
            "error": str(exc),
        }
