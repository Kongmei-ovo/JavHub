"""Operations overview API for the inventory workflow."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query
from fastapi.params import Query as QueryParam

from config import config
from database import (
    count_snapshot_actors,
    download_candidate_stats,
    get_inventory_jobs,
    get_latest_snapshot_key,
    list_candidate_process_runs,
    mapping_summary_for_snapshot,
    missing_videos_summary,
    variant_group_stats,
)
from services import cache
from services.data_quality import build_data_quality_overview
from services.supplement_repair_progress import data_quality_repair_progress, get_supplement_status

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
_CACHE_NAMESPACE = "operations_overview"
_CACHE_TTL = 15


@router.get("/overview")
async def operations_overview(cache_control: str | None = Query(None, alias="cache")) -> dict[str, Any]:
    _cache_control = None if isinstance(cache_control, QueryParam) else cache_control
    cache_bypass = cache.should_bypass_response_cache(_cache_control)

    async def produce() -> dict[str, Any]:
        snapshot_key = get_latest_snapshot_key()
        snapshot_actor_count = count_snapshot_actors(snapshot_key)
        candidate_stats = download_candidate_stats()
        jobs = get_inventory_jobs(limit=10)
        missing = missing_videos_summary(limit=8)
        variant_index = variant_group_stats()

        supplement = await get_supplement_status()
        repair_progress = data_quality_repair_progress(supplement)
        if repair_progress:
            data_quality = build_data_quality_overview(limit=8, repair_progress=repair_progress)
        else:
            data_quality = build_data_quality_overview(limit=8)

        return {
            "status": "ok",
            "automation": config.automation,
            "snapshot": {
                "snapshot_key": snapshot_key,
                "actor_count": snapshot_actor_count,
            },
            "mapping": {
                **mapping_summary_for_snapshot(snapshot_key),
                "auto_match": config.actor_mapping,
            },
            "missing": {
                "total": missing["total"],
                "top_actresses": missing["top_actresses"],
            },
            "candidates": {
                **candidate_stats,
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
            "variant_index": variant_index,
            "data_quality": data_quality,
        }

    if cache_bypass:
        return await cache.get_or_set_response(
            _CACHE_NAMESPACE,
            {},
            produce,
            ttl=_CACHE_TTL,
            bypass=True,
        )
    return await cache.get_or_set_response(_CACHE_NAMESPACE, {}, produce, ttl=_CACHE_TTL)


@router.post("/candidate-processing/run")
async def run_candidate_processing_now() -> dict[str, Any]:
    from services.candidate_processor import run_automatic_candidate_processing

    result = await run_automatic_candidate_processing(operator="manual")
    action = str(result.get("action") or "")
    return {
        **result,
        "dry_run": bool(result.get("dry_run", False)),
        "manual_noop": action == "manual_policy",
        "effective": action not in {"manual_policy", "busy"},
    }

def _candidate_schedule_state() -> dict[str, Any]:
    try:
        from scheduler.tasks import candidate_auto_process_schedule_state

        state = candidate_auto_process_schedule_state()
    except Exception as exc:
        state = {
            "enabled": False,
            "running": False,
            "next_run_time": None,
            "error": str(exc),
        }
    policy = str(config.automation_download_policy or "manual").lower()
    enabled = bool(state.get("enabled"))
    disabled_reason = str(state.get("error") or "")
    if policy == "manual":
        effective_enabled = False
        disabled_reason = disabled_reason or "manual_policy"
    elif not enabled:
        effective_enabled = False
        disabled_reason = disabled_reason or "schedule_disabled"
    else:
        effective_enabled = True
    return {
        **state,
        "policy": policy,
        "effective_enabled": effective_enabled,
        "disabled_reason": disabled_reason,
    }
