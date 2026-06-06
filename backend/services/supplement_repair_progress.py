"""Supplement job repair-progress helpers for data-quality prioritization."""
from __future__ import annotations

import asyncio
import re
from typing import Any


async def get_supplement_status() -> dict[str, Any]:
    supplement: dict[str, Any] = {"available": False}
    try:
        from modules.info_client import get_info_client

        client = get_info_client()
        stats, queued, running, failed = await asyncio.gather(
            client.proxy_get("/api/v1/supplement/stats", params=None),
            client.proxy_get(
                "/api/v1/supplement/jobs",
                params={"page": 1, "page_size": 1, "status": "queued"},
            ),
            client.proxy_get(
                "/api/v1/supplement/jobs",
                params={"page": 1, "page_size": 1, "status": "running"},
            ),
            client.proxy_get(
                "/api/v1/supplement/jobs",
                params={"page": 1, "page_size": 5, "status": "failed"},
            ),
        )
        failed_samples = _failed_job_samples(failed)
        supplement = {
            "available": True,
            "stats": stats,
            "queued": _total_from_response(queued),
            "running": _total_from_response(running),
            "failed": _total_from_response(failed),
        }
        if failed_samples:
            supplement["failed_samples"] = failed_samples
    except Exception as exc:
        supplement = {"available": False, "error": str(exc)}
    return supplement


async def get_supplement_repair_progress() -> dict[str, dict[str, Any]]:
    return data_quality_repair_progress(await get_supplement_status())


def data_quality_repair_progress(supplement: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not supplement.get("available"):
        return {}
    failed_samples = supplement.get("failed_samples") if isinstance(supplement.get("failed_samples"), list) else []
    return {
        "low_quality_cover": {
            "available": True,
            "queued": int(supplement.get("queued") or 0),
            "running": int(supplement.get("running") or 0),
            "failed": int(supplement.get("failed") or 0),
            "failed_reasons": failed_job_reasons(failed_samples),
            "provider_failures": failed_job_providers(failed_samples),
        },
    }


def failed_job_providers(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for sample in samples:
        route_source = str(sample.get("source") or "").strip()
        for provider in failed_job_provider_names(str(sample.get("last_error") or "")):
            entry = counts.setdefault(provider, {"provider": provider, "count": 0})
            entry["count"] = int(entry["count"]) + 1
            if route_source == "all":
                entry["route_source"] = "all"
            elif route_source == provider and entry.get("route_source") != "all":
                entry["route_source"] = provider
    return [
        entry
        for _, entry in sorted(counts.items(), key=lambda item: (-int(item[1]["count"]), item[0]))
    ]


def failed_job_reasons(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels: dict[str, int] = {}
    for sample in samples:
        label = failed_job_reason_label(str(sample.get("last_error") or ""))
        labels[label] = labels.get(label, 0) + 1
    order = {"来源暂不可用": 0, "低置信匹配": 1, "请求失败": 2, "其他失败": 3}
    return [
        {"label": label, "count": count}
        for label, count in sorted(labels.items(), key=lambda item: (-item[1], order.get(item[0], 99), item[0]))
    ]


def failed_job_provider_names(last_error: str) -> list[str]:
    text = last_error.lower()
    prefix = re.match(r"^\s*([a-z0-9_.-]+)\s*:", text)
    known = {"avbase", "fanza", "fc2", "jav321", "javbus", "javlibrary", "mgstage"}
    if prefix and prefix.group(1) in known:
        return [prefix.group(1)]
    return sorted(provider for provider in known if provider in text)


def failed_job_reason_label(last_error: str) -> str:
    text = last_error.lower()
    if "temporarily unavailable" in text or "source health control" in text or "cloudflare" in text:
        return "来源暂不可用"
    if "no high-confidence" in text or "low quality detail" in text or "identity_unknown" in text:
        return "低置信匹配"
    if "request failed" in text or "not found" in text or "forbidden" in text or "403" in text or "404" in text:
        return "请求失败"
    return "其他失败"


def _failed_job_samples(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    rows = value.get("data") or value.get("items") or []
    if not isinstance(rows, list):
        return []
    samples: list[dict[str, Any]] = []
    for row in rows[:5]:
        if not isinstance(row, dict):
            continue
        last_error = str(row.get("last_error") or row.get("error") or "").strip()
        if last_error:
            sample = {"last_error": last_error}
            source = str(row.get("source") or "").strip()
            if source:
                sample["source"] = source
            samples.append(sample)
    return samples


def _total_from_response(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(value.get("total") or value.get("total_count") or 0)
