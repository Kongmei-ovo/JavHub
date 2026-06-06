"""Supplement job repair-progress helpers for data-quality prioritization."""
from __future__ import annotations

import asyncio
import re
from typing import Any

_FAILED_SAMPLE_LIMIT = 5
_FAILED_DIAGNOSTIC_PAGE_SIZE = 100
_FAILED_DIAGNOSTIC_LIMIT = 500


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
                params={"page": 1, "page_size": _FAILED_DIAGNOSTIC_PAGE_SIZE, "status": "failed"},
            ),
        )
        failed_diagnostics = await _failed_job_diagnostics(client, failed)
        failed_samples = failed_diagnostics[:_FAILED_SAMPLE_LIMIT]
        supplement = {
            "available": True,
            "stats": stats,
            "queued": _total_from_response(queued),
            "running": _total_from_response(running),
            "failed": _total_from_response(failed),
        }
        if failed_samples:
            supplement["failed_samples"] = failed_samples
        if failed_diagnostics:
            supplement["failed_diagnostics"] = failed_diagnostics
    except Exception as exc:
        supplement = {"available": False, "error": str(exc)}
    return supplement


async def get_supplement_repair_progress() -> dict[str, dict[str, Any]]:
    return data_quality_repair_progress(await get_supplement_status())


def data_quality_repair_progress(supplement: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not supplement.get("available"):
        return {}
    failed_diagnostics = supplement.get("failed_diagnostics")
    if not isinstance(failed_diagnostics, list):
        failed_diagnostics = supplement.get("failed_samples") if isinstance(supplement.get("failed_samples"), list) else []
    return {
        "low_quality_cover": {
            "available": True,
            "queued": int(supplement.get("queued") or 0),
            "running": int(supplement.get("running") or 0),
            "failed": int(supplement.get("failed") or 0),
            "failed_reasons": failed_job_reasons(failed_diagnostics),
            "provider_failures": failed_job_providers(failed_diagnostics),
        },
    }


def failed_job_providers(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], dict[str, Any]] = {}
    for sample in samples:
        route_source = str(sample.get("source") or "").strip()
        last_error = str(sample.get("last_error") or "")
        providers = failed_job_provider_names(last_error)
        if not providers and route_source in _known_failed_job_providers():
            providers = [route_source]
        for provider in providers:
            provider_route_source = "all" if route_source == "all" else provider
            entry = counts.setdefault(
                (provider, provider_route_source),
                {"provider": provider, "count": 0, "route_source": provider_route_source, "_weight": 0},
            )
            entry["count"] = int(entry["count"]) + 1
            entry["_weight"] = max(
                int(entry.get("_weight") or 0),
                _failed_job_provider_failure_weight(last_error, provider),
            )
    return [
        {key: value for key, value in entry.items() if key != "_weight"}
        for _, entry in sorted(counts.items(), key=_failed_job_provider_sort_key)
    ]


def failed_job_reasons(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels: dict[str, int] = {}
    for sample in samples:
        label = failed_job_reason_label(str(sample.get("last_error") or ""))
        labels[label] = labels.get(label, 0) + 1
    order = {"来源暂不可用": 0, "并发限制": 1, "来源数据结构异常": 2, "写入异常": 3, "低置信匹配": 4, "请求失败": 5, "其他失败": 6}
    return [
        {"label": label, "count": count}
        for label, count in sorted(labels.items(), key=lambda item: (-item[1], order.get(item[0], 99), item[0]))
    ]


def failed_job_provider_names(last_error: str) -> list[str]:
    text = last_error.lower()
    prefix = re.match(r"^\s*([a-z0-9_.-]+)\s*:", text)
    known = _known_failed_job_providers()
    if prefix and prefix.group(1) in known:
        return [prefix.group(1)]
    return sorted(provider for provider in known if provider in text)


def _failed_job_provider_sort_key(item: tuple[tuple[str, str], dict[str, Any]]) -> tuple[int, int, str, str]:
    (provider, route_source), entry = item
    return (-int(entry["count"]), -int(entry.get("_weight") or 0), provider, route_source)


def _known_failed_job_providers() -> set[str]:
    return {"avbase", "fanza", "fc2", "jav321", "javbus", "javlibrary", "mgstage"}


def failed_job_reason_label(last_error: str) -> str:
    text = last_error.lower()
    if "concurrency limit" in text:
        return "并发限制"
    if "cannot unmarshal" in text or "low quality detail" in text:
        return "来源数据结构异常"
    if "sqlstate" in text or "not-null constraint" in text or "null value in column" in text:
        return "写入异常"
    if "temporarily unavailable" in text or "source health control" in text or "cloudflare" in text:
        return "来源暂不可用"
    if "no high-confidence" in text or "identity_unknown" in text:
        return "低置信匹配"
    if "request failed" in text or "not found" in text or "forbidden" in text or "403" in text or "404" in text:
        return "请求失败"
    return "其他失败"


def _failed_job_provider_failure_weight(last_error: str, provider: str) -> int:
    fragment = _failed_job_provider_error_fragment(last_error, provider)
    if re.search(r"cloudflare|temporarily unavailable|source health control", fragment):
        return 70
    if re.search(r"forbidden|403", fragment):
        return 60
    if re.search(r"request failed|not found|404", fragment):
        return 40
    if "concurrency limit" in fragment:
        return 30
    if "cannot unmarshal" in fragment or "low quality detail" in fragment:
        return 25
    if "no high-confidence" in fragment or "identity_unknown" in fragment:
        return 10
    return 1 if fragment else 0


def _failed_job_provider_error_fragment(last_error: str, provider: str) -> str:
    text = str(last_error or "").lower()
    provider_name = str(provider or "").lower()
    start = text.find(f"{provider_name}:")
    if start < 0:
        return text if provider_name and provider_name in text else ""
    rest = text[start:]
    next_indexes = [
        rest.find(f"; {name}:")
        for name in _known_failed_job_providers()
        if name != provider_name
    ]
    next_indexes = [index for index in next_indexes if index >= 0]
    end = min(next_indexes) if next_indexes else len(rest)
    return rest[:end]


def _failed_job_samples(value: Any, limit: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    rows = value.get("data") or value.get("items") or []
    if not isinstance(rows, list):
        return []
    samples: list[dict[str, Any]] = []
    selected_rows = rows[:limit] if limit is not None else rows
    for row in selected_rows:
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


async def _failed_job_diagnostics(client: Any, first_page: Any) -> list[dict[str, Any]]:
    samples = _failed_job_samples(first_page)
    total = min(_total_from_response(first_page), _FAILED_DIAGNOSTIC_LIMIT)
    fetched = _rows_len(first_page)
    if fetched <= 0:
        return samples
    page = 2
    while fetched < total:
        page_response = await client.proxy_get(
            "/api/v1/supplement/jobs",
            params={"page": page, "page_size": _FAILED_DIAGNOSTIC_PAGE_SIZE, "status": "failed"},
        )
        row_count = _rows_len(page_response)
        if row_count <= 0:
            break
        samples.extend(_failed_job_samples(page_response))
        fetched += row_count
        page += 1
    return samples[:_FAILED_DIAGNOSTIC_LIMIT]


def _rows_len(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    rows = value.get("data") or value.get("items") or []
    return len(rows) if isinstance(rows, list) else 0


def _total_from_response(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(value.get("total") or value.get("total_count") or 0)
