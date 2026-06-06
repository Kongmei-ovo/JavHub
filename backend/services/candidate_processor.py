"""Download candidate enrichment and automation policy processing."""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from typing import Any

from config import config
from database import (
    add_candidate_process_run,
    add_download_candidate_event,
    count_auto_sent_candidates_since,
    get_candidate_process_run,
    get_download_candidate,
    get_download_task,
    is_video_exempt,
    list_download_candidates,
    set_download_candidate_status,
    update_download_candidate_magnet,
)
from services.downloader import downloader_service
from sources import register_all_sources
from sources.registry import SourceRegistry


POLICIES = {"manual", "rules", "auto"}
PROCESSABLE_STATUSES = {"candidate", "failed"}
_PROCESSING_LOCK = threading.Lock()


@dataclass(frozen=True)
class AutomationPolicy:
    download_policy: str
    candidate_sources: tuple[str, ...]
    rules_require_magnet: bool = True
    max_auto_downloads_per_run: int = 20
    max_auto_downloads_per_24h: int = 100

    @classmethod
    def from_config(cls) -> "AutomationPolicy":
        return cls(
            download_policy=config.automation_download_policy,
            candidate_sources=tuple(config.automation_candidate_sources),
            rules_require_magnet=config.automation_rules_require_magnet,
            max_auto_downloads_per_run=config.automation_max_auto_downloads_per_run,
            max_auto_downloads_per_24h=config.automation_max_auto_downloads_per_24h,
        )

    def source_allowed(self, source: str | None) -> bool:
        return not self.candidate_sources or str(source or "manual") in self.candidate_sources


def _response(action: str, candidate: dict | None = None, **extra) -> dict:
    return {
        "status": "ok",
        "action": action,
        "candidate": candidate,
        **extra,
    }


def is_candidate_processing_running() -> bool:
    return _PROCESSING_LOCK.locked()


def _busy_response() -> dict:
    return {
        "status": "busy",
        "action": "busy",
        "total": 0,
        "counts": {},
        "results": [],
    }


def _code_for_candidate(candidate: dict) -> str:
    return str(candidate.get("dvd_id") or candidate.get("content_id") or "").strip()


def _normalize_policy(policy: str | None) -> str:
    chosen_policy = str(policy or config.automation_download_policy or "manual").lower()
    return chosen_policy if chosen_policy in POLICIES else "manual"


def _candidate_plan(
    candidate: dict,
    chosen_policy: str,
    policy_cfg: AutomationPolicy,
    enrich: bool,
    force: bool,
) -> dict:
    status = candidate.get("status")
    if status not in PROCESSABLE_STATUSES:
        return {"action": "skipped_status", "reason": f"status={status}", "candidate": candidate, "policy": chosen_policy}

    if not force and not policy_cfg.source_allowed(candidate.get("source")):
        return {"action": "skipped_source", "reason": f"source={candidate.get('source')}", "candidate": candidate, "policy": chosen_policy}

    code = _code_for_candidate(candidate)
    if code and is_video_exempt(code):
        return {"action": "skipped_exempt", "reason": f"exempt={code}", "candidate": candidate, "policy": chosen_policy}

    if chosen_policy == "manual" and not force:
        return {"action": "manual_required", "reason": "manual policy", "candidate": candidate, "policy": chosen_policy}

    if _download_uri(candidate):
        return {"action": "would_send", "reason": "ready", "candidate": candidate, "policy": chosen_policy}

    if enrich and chosen_policy in {"rules", "auto"}:
        return {"action": "would_enrich_magnet", "reason": "missing magnet", "candidate": candidate, "policy": chosen_policy}

    if chosen_policy == "rules" and policy_cfg.rules_require_magnet:
        return {"action": "skipped_missing_magnet", "reason": "rules require magnet", "candidate": candidate, "policy": chosen_policy}

    return {"action": "failed_missing_magnet", "reason": "missing magnet", "candidate": candidate, "policy": chosen_policy}


def _sent_in_results(results: list[dict]) -> int:
    return sum(1 for result in results if result.get("action") == "sent")


def _download_limit_state(policy_cfg: AutomationPolicy) -> dict:
    sent_24h = count_auto_sent_candidates_since(24)
    per_run = policy_cfg.max_auto_downloads_per_run
    per_24h = policy_cfg.max_auto_downloads_per_24h
    remaining_24h = per_24h - sent_24h if per_24h > 0 else None
    remaining = per_run if per_run > 0 else None
    if remaining_24h is not None:
        remaining = remaining_24h if remaining is None else min(remaining, remaining_24h)
    return {
        "per_run": per_run,
        "per_24h": per_24h,
        "sent_24h": sent_24h,
        "remaining": remaining,
        "remaining_24h": remaining_24h,
    }


def _size_to_mb(value: str | None) -> float:
    text = str(value or "").strip().upper().replace(",", "")
    if not text:
        return 0
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB|MB|KB)?", text)
    if not match:
        return 0
    number = float(match.group(1))
    unit = match.group(2) or "MB"
    if unit == "TB":
        return number * 1024 * 1024
    if unit == "GB":
        return number * 1024
    if unit == "KB":
        return number / 1024
    return number


def _magnet_score(item: dict) -> tuple:
    title = str(item.get("title") or "").lower()
    quality = str(item.get("quality") or "").lower()
    resolution = str(item.get("resolution") or "").lower()
    subtitle = bool(item.get("subtitle")) or any(token in title for token in ("字幕", "subtitle", "sub"))
    hd = bool(item.get("hd")) or "1080" in title or "2160" in title or "4k" in title or "hd" in quality
    res_score = 0
    if "2160" in resolution or "2160" in title or "4k" in title:
        res_score = 4
    elif "1080" in resolution or "1080" in title:
        res_score = 3
    elif "720" in resolution or "720" in title:
        res_score = 2
    size_score = _size_to_mb(item.get("size"))
    return (1 if subtitle else 0, 1 if hd else 0, res_score, size_score)


def _download_uri(item: dict) -> str:
    for key in ("magnet", "torrent_url", "download_url"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def classify_candidate_error(message: Any = None, status: int | str | None = None) -> dict:
    text = str(message or "").lower()
    status_code = _status_code(status)

    category = "unknown"
    retryable = True
    if (
        "missing magnet" in text
        or "no magnet" in text
        or "magnet_not_found" in text
        or "未找到可用 magnet" in text
        or "候选缺少 magnet" in text
    ):
        category = "missing_magnet"
        retryable = False
    elif isinstance(message, TimeoutError) or status_code in {408, 504} or "timeout" in text or "timed out" in text:
        category = "source_timeout"
        retryable = True
    elif (
        status_code in {401, 403}
        or isinstance(message, PermissionError)
        or "unauthorized" in text
        or "forbidden" in text
        or "authentication" in text
        or "api key" in text
        or "token" in text
    ):
        category = "downloader_auth"
        retryable = False
    elif status_code == 409 or "duplicate" in text or "already exists" in text or "already exist" in text:
        category = "duplicate"
        retryable = False
    elif status_code in {400, 422} or "rejected" in text or "invalid path" in text or "invalid request" in text:
        category = "remote_rejected"
        retryable = False

    return {"error_category": category, "retryable": retryable}


def _status_code(status: int | str | None) -> int | None:
    if status is None:
        return None
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def _failure_event_detail(message: Any, status: int | str | None = None) -> str:
    payload = {
        "error": str(message),
        **classify_candidate_error(message, status),
    }
    status_code = _status_code(status)
    if status_code is not None:
        payload["status"] = status_code
    return json.dumps(payload, ensure_ascii=False)


async def find_best_magnet(candidate: dict) -> dict | None:
    """Search registered sources and select the best available download URI."""
    register_all_sources()
    keywords = []
    for value in (candidate.get("dvd_id"), candidate.get("content_id")):
        value = str(value or "").strip()
        if value and value not in keywords:
            keywords.append(value)

    best: dict | None = None
    for keyword in keywords:
        results = await SourceRegistry.search_all(keyword)
        for item in results:
            if not _download_uri(item):
                continue
            if best is None or _magnet_score(item) > _magnet_score(best):
                best = dict(item)
    return best


async def enrich_candidate_magnet(candidate_id: int, operator: str = "manual") -> dict:
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        return _response("not_found", None)
    if candidate.get("magnet"):
        add_download_candidate_event(candidate_id, "magnet_enrich_skipped", "candidate already has magnet", operator)
        return _response("already_has_magnet", candidate)

    best = await find_best_magnet(candidate)
    if not best:
        add_download_candidate_event(candidate_id, "magnet_enrich_failed", "no magnet found", operator)
        return _response("magnet_not_found", candidate)

    updated = update_download_candidate_magnet(
        candidate_id,
        _download_uri(best),
        str(best.get("source") or best.get("name") or "sources"),
    )
    add_download_candidate_event(
        candidate_id,
        "magnet_enriched",
        str(best.get("title") or best.get("size") or "sources"),
        operator,
    )
    return _response("magnet_enriched", updated, magnet=best)


async def process_candidate(
    candidate_id: int,
    policy: str | None = None,
    enrich: bool = True,
    force: bool = False,
    operator: str = "manual",
    send_limit_remaining: int | None = None,
) -> dict:
    candidate = get_download_candidate(candidate_id)
    if not candidate:
        return _response("not_found", None)

    chosen_policy = _normalize_policy(policy)
    policy_cfg = AutomationPolicy.from_config()
    plan = _candidate_plan(candidate, chosen_policy, policy_cfg, enrich, force)
    planned_action = plan["action"]
    if planned_action in {"skipped_status", "skipped_source", "skipped_exempt", "manual_required"}:
        add_download_candidate_event(candidate_id, "policy_skipped", plan["reason"], operator)
        return _response(planned_action, candidate, policy=chosen_policy)

    if enrich and not _download_uri(candidate):
        enrich_result = await enrich_candidate_magnet(candidate_id, operator=operator)
        candidate = get_download_candidate(candidate_id) or candidate
        if not _download_uri(candidate) and chosen_policy in {"rules", "auto"}:
            if chosen_policy == "auto":
                error_msg = "未找到可用 magnet"
                failed = set_download_candidate_status(candidate_id, "failed", error_msg=error_msg)
                metadata = classify_candidate_error(error_msg)
                add_download_candidate_event(candidate_id, "process_failed", _failure_event_detail(error_msg), operator)
                return _response(
                    "failed_missing_magnet",
                    failed,
                    policy=chosen_policy,
                    enrich_result=enrich_result,
                    **metadata,
                )
            add_download_candidate_event(candidate_id, "policy_skipped", "missing magnet", operator)
            return _response("skipped_missing_magnet", candidate, policy=chosen_policy, enrich_result=enrich_result)

    if chosen_policy == "rules" and policy_cfg.rules_require_magnet and not _download_uri(candidate):
        add_download_candidate_event(candidate_id, "policy_skipped", "rules require magnet", operator)
        return _response("skipped_missing_magnet", candidate, policy=chosen_policy)

    download_uri = _download_uri(candidate)
    if not download_uri:
        error_msg = "候选缺少 magnet，不能下发下载"
        failed = set_download_candidate_status(candidate_id, "failed", error_msg=error_msg)
        metadata = classify_candidate_error(error_msg)
        add_download_candidate_event(candidate_id, "process_failed", _failure_event_detail(error_msg), operator)
        return _response("failed_missing_magnet", failed, policy=chosen_policy, **metadata)

    if send_limit_remaining is not None and send_limit_remaining <= 0 and not force:
        add_download_candidate_event(candidate_id, "policy_skipped", "auto download limit reached", operator)
        return _response("skipped_limit", candidate, policy=chosen_policy)

    try:
        task_id = await downloader_service.create_download_task(
            code=candidate.get("content_id") or candidate.get("dvd_id") or "",
            title=candidate.get("title") or candidate.get("content_id") or "",
            magnet=download_uri,
            path="",
        )
    except Exception as exc:
        failed = set_download_candidate_status(candidate_id, "failed", error_msg=str(exc))
        metadata = classify_candidate_error(exc)
        add_download_candidate_event(candidate_id, "process_failed", _failure_event_detail(exc), operator)
        return _response("failed_downloader", failed, policy=chosen_policy, error=str(exc), **metadata)

    task = get_download_task(task_id)
    if task and task.get("status") == "failed":
        error_msg = task.get("error_msg") or "下载任务创建失败"
        failed = set_download_candidate_status(candidate_id, "failed", error_msg=error_msg)
        error_status = task.get("status_code") or task.get("http_status")
        metadata = classify_candidate_error(error_msg, error_status)
        add_download_candidate_event(candidate_id, "process_failed", _failure_event_detail(error_msg, error_status), operator)
        return _response(
            "failed_downloader",
            failed,
            policy=chosen_policy,
            download_task_id=task_id,
            error=error_msg,
            **metadata,
        )

    updated = set_download_candidate_status(candidate_id, "sent", download_task_id=task_id)
    event = "auto_approved" if operator == "system" or chosen_policy in {"rules", "auto"} else "approved"
    add_download_candidate_event(candidate_id, event, f"download_task_id={task_id}", operator)
    return _response("sent", updated, policy=chosen_policy, download_task_id=task_id)


async def process_candidates(
    filters: dict[str, Any] | None = None,
    policy: str | None = None,
    enrich: bool = True,
    limit: int = 50,
    force: bool = False,
    operator: str = "manual",
) -> dict:
    filters = filters or {}
    chosen_policy = _normalize_policy(policy)
    policy_cfg = AutomationPolicy.from_config()
    limit_state = _download_limit_state(policy_cfg)
    send_limit_remaining = limit_state["remaining"]
    rows = list_download_candidates(
        status=filters.get("status") or "candidate",
        actress_id=filters.get("actress_id"),
        source=filters.get("source"),
        q=filters.get("q"),
        needs_magnet=filters.get("needs_magnet"),
        missing_cover=filters.get("missing_cover"),
        latest_event_action=filters.get("latest_event_action"),
        limit=limit,
    )
    results = []
    for row in rows:
        result = await process_candidate(
            row["id"],
            policy=chosen_policy,
            enrich=enrich,
            force=force,
            operator=operator,
            send_limit_remaining=send_limit_remaining,
        )
        results.append(result)
        if send_limit_remaining is not None and result.get("action") == "sent":
            send_limit_remaining -= 1
    counts: dict[str, int] = {}
    for result in results:
        action = result.get("action") or "unknown"
        counts[action] = counts.get(action, 0) + 1
    result = {
        "status": "ok",
        "total": len(results),
        "counts": counts,
        "limits": limit_state,
        "results": results,
    }
    result["run_id"] = add_candidate_process_run(
        trigger_source=operator,
        policy=chosen_policy,
        filters={**filters, "limit": limit, "enrich": enrich, "force": force},
        result=result,
    )
    return result


async def preview_candidates(
    filters: dict[str, Any] | None = None,
    policy: str | None = None,
    enrich: bool = True,
    limit: int = 50,
    force: bool = False,
) -> dict:
    filters = filters or {}
    chosen_policy = _normalize_policy(policy)
    policy_cfg = AutomationPolicy.from_config()
    limit_state = _download_limit_state(policy_cfg)
    send_remaining = limit_state["remaining"]
    rows = list_download_candidates(
        status=filters.get("status") or "candidate",
        actress_id=filters.get("actress_id"),
        source=filters.get("source"),
        q=filters.get("q"),
        needs_magnet=filters.get("needs_magnet"),
        missing_cover=filters.get("missing_cover"),
        latest_event_action=filters.get("latest_event_action"),
        limit=limit,
    )
    results = []
    for row in rows:
        plan = _candidate_plan(row, chosen_policy, policy_cfg, enrich, force)
        action = plan["action"]
        if action == "would_send":
            if send_remaining is not None and send_remaining <= 0 and not force:
                action = "would_skip_limit"
            elif send_remaining is not None:
                send_remaining -= 1
        results.append({**plan, "action": action})
    counts = _count_actions(results)
    return {
        "status": "ok",
        "dry_run": True,
        "policy": chosen_policy,
        "total": len(results),
        "counts": counts,
        "limits": limit_state,
        "results": results,
    }


def _count_actions(results: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        action = result.get("action") or "unknown"
        counts[action] = counts.get(action, 0) + 1
    return counts


def _failed_candidate_ids_from_run(run: dict) -> list[int]:
    ids: list[int] = []
    for result in (run.get("result") or {}).get("results") or []:
        action = str(result.get("action") or "")
        candidate = result.get("candidate") or {}
        candidate_id = candidate.get("id")
        if action.startswith("failed") and candidate_id and int(candidate_id) not in ids:
            ids.append(int(candidate_id))
    return ids


async def retry_failed_candidates_from_run(
    run_id: int,
    enrich: bool = True,
    force: bool = False,
    operator: str = "manual",
) -> dict:
    run = get_candidate_process_run(run_id)
    if not run:
        return {"status": "ok", "action": "not_found", "total": 0, "counts": {}, "results": []}

    candidate_ids = _failed_candidate_ids_from_run(run)
    policy = str(run.get("policy") or config.automation_download_policy or "manual").lower()
    if policy not in POLICIES:
        policy = "manual"

    results = []
    for candidate_id in candidate_ids:
        results.append(
            await process_candidate(
                candidate_id,
                policy=policy,
                enrich=enrich,
                force=force,
                operator=operator,
            )
        )
    result = {
        "status": "ok",
        "action": "retried_failed_run",
        "source_run_id": run_id,
        "total": len(results),
        "counts": _count_actions(results),
        "results": results,
    }
    result["run_id"] = add_candidate_process_run(
        trigger_source=f"{operator}:retry_run",
        policy=policy,
        filters={"source_run_id": run_id, "candidate_ids": candidate_ids, "enrich": enrich, "force": force},
        result=result,
    )
    return result


async def run_automatic_candidate_processing(limit: int = 50, operator: str = "system") -> dict:
    if not _PROCESSING_LOCK.acquire(blocking=False):
        return _busy_response()
    policy = config.automation_download_policy
    policy_cfg = AutomationPolicy.from_config()
    effective_limit = limit
    if policy_cfg.max_auto_downloads_per_run > 0:
        effective_limit = min(limit, policy_cfg.max_auto_downloads_per_run)
    try:
        if policy == "manual":
            result = {
                "status": "ok",
                "action": "manual_policy",
                "skipped": True,
                "reason": "manual policy",
                "total": 0,
                "counts": {},
                "results": [],
            }
            result["run_id"] = add_candidate_process_run(
                trigger_source=operator,
                policy=policy,
                filters={"status": "candidate", "limit": effective_limit},
                result=result,
            )
            return result
        return await process_candidates(
            filters={"status": "candidate"},
            policy=policy,
            enrich=True,
            limit=effective_limit,
            force=False,
            operator=operator,
        )
    finally:
        _PROCESSING_LOCK.release()
