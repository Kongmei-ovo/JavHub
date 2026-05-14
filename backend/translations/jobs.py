from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from config import config
from database import (
    add_translation_job,
    get_cached_translation,
    get_translation_job,
    list_translation_jobs,
    update_translation_job,
    upsert_translation,
)
from modules.info_client import get_info_client
from translations.service import TranslatorService

logger = logging.getLogger(__name__)

_running_jobs: dict[int, asyncio.Task] = {}

METADATA_ENTITY_TYPES = ("category", "series", "maker", "label", "actress")
METADATA_JOB_TYPES: dict[str, tuple[str, ...]] = {
    "metadata_names": METADATA_ENTITY_TYPES,
    "metadata_categories": ("category",),
    "metadata_series": ("series",),
    "metadata_makers": ("maker",),
    "metadata_labels": ("label",),
    "metadata_actresses": ("actress",),
}
ALLOWED_JOB_TYPES = {"library_titles", *METADATA_JOB_TYPES.keys()}

_METADATA_TEXT_KEYS = {
    "category": ("name_ja", "name_en", "name"),
    "series": ("name_ja", "name_en", "name"),
    "maker": ("name_ja", "name_en", "name"),
    "label": ("name_ja", "name_en", "name"),
    "actress": ("name_kanji", "name_ja", "name_romaji", "name"),
}


def _normalize_code(value: Any) -> str:
    return str(value or "").replace("-", "").replace("_", "").lower()


def _title_text(item: dict) -> str:
    return str(item.get("title_ja") or item.get("title_en") or item.get("title") or "").strip()


def _content_id(item: dict) -> str:
    return str(item.get("content_id") or item.get("dvd_id") or item.get("canonical_number") or "").strip()


def _batch_order(provider_order: list[str] | None = None) -> list[str]:
    if provider_order:
        return provider_order
    return config.translation_batch_provider_order


async def create_translation_job(
    job_type: str = "library_titles",
    *,
    provider_order: list[str] | None = None,
    limit: int = 1000,
    force: bool = False,
) -> dict:
    if job_type not in ALLOWED_JOB_TYPES:
        raise ValueError(f"job_type must be one of: {', '.join(sorted(ALLOWED_JOB_TYPES))}")
    order = _batch_order(provider_order)
    job_id = add_translation_job(job_type, scope="library", provider_order=order)
    task = asyncio.create_task(_run_job(job_id, job_type, order, limit=limit, force=force))
    _running_jobs[job_id] = task
    task.add_done_callback(lambda _: _running_jobs.pop(job_id, None))
    return get_translation_job(job_id) or {"id": job_id, "status": "pending"}


def list_jobs(limit: int = 50) -> list[dict]:
    return list_translation_jobs(limit=limit)


def get_job(job_id: int) -> dict | None:
    job = get_translation_job(job_id)
    if job:
        job["running"] = job_id in _running_jobs
    return job


async def _run_job(job_id: int, job_type: str, provider_order: list[str], *, limit: int, force: bool) -> None:
    counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
    update_translation_job(
        job_id,
        status="running",
        started_at=datetime.utcnow().isoformat(timespec="seconds"),
        result={"provider_order": provider_order, "limit": limit, "force": force},
    )
    try:
        if job_type == "library_titles":
            items = await _collect_library_titles(limit)
            update_translation_job(job_id, total=len(items))
            await _translate_titles(job_id, items, provider_order, counters, force=force)
        elif job_type in METADATA_JOB_TYPES:
            items = await _collect_metadata_names(METADATA_JOB_TYPES[job_type], limit=limit)
            update_translation_job(job_id, total=len(items))
            await _translate_metadata_names(job_id, items, provider_order, counters, force=force)
        update_translation_job(
            job_id,
            status="completed",
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={"provider_order": provider_order, "limit": limit, "force": force, **counters},
        )
    except Exception as exc:
        logger.exception("Translation job %s failed", job_id)
        update_translation_job(
            job_id,
            status="failed",
            error_msg=str(exc),
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={"provider_order": provider_order, "limit": limit, "force": force, **counters},
        )


async def _collect_library_titles(limit: int) -> list[dict]:
    client = get_info_client()
    items: list[dict] = []
    page = 1
    page_size = min(max(limit, 1), 100)
    while len(items) < limit:
        result = await client.list_videos(page=page, page_size=min(page_size, limit - len(items)))
        page_items = result.get("data", []) if isinstance(result, dict) else []
        if not page_items:
            break
        items.extend(page_items)
        total_pages = int(result.get("total_pages") or 1) if isinstance(result, dict) else 1
        if page >= total_pages:
            break
        page += 1
    return items


def _metadata_text(item: dict, entity_type: str) -> str:
    for key in _METADATA_TEXT_KEYS.get(entity_type, ("name",)):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _append_metadata_row(rows: list[dict], entity_type: str, item: dict, limit: int | None) -> bool:
    if limit is not None and len(rows) >= limit:
        return False
    rows.append({"type": entity_type, "id": item.get("id"), "text": _metadata_text(item, entity_type)})
    return True


async def _collect_metadata_names(entity_types: tuple[str, ...] | None = None, limit: int | None = None) -> list[dict]:
    client = get_info_client()
    requested = tuple(entity_types or METADATA_ENTITY_TYPES)
    capped_limit = max(1, limit) if isinstance(limit, int) and limit > 0 else None
    rows: list[dict] = []

    if "category" in requested:
        type_rows: list[dict] = []
        for item in await client.list_categories():
            if not _append_metadata_row(type_rows, "category", item, capped_limit):
                break
        rows.extend(type_rows)

    if "series" in requested:
        type_rows = []
        for item in await client.list_series():
            if not _append_metadata_row(type_rows, "series", item, capped_limit):
                break
        rows.extend(type_rows)

    if "maker" in requested:
        type_rows = []
        makers = await client.list_makers()
        for item in makers if isinstance(makers, list) else []:
            if not _append_metadata_row(type_rows, "maker", item, capped_limit):
                break
        rows.extend(type_rows)

    if "label" in requested and hasattr(client, "list_labels"):
        type_rows = []
        labels = await client.list_labels()
        for item in labels if isinstance(labels, list) else []:
            if not _append_metadata_row(type_rows, "label", item, capped_limit):
                break
        rows.extend(type_rows)

    if "actress" in requested:
        type_rows = []
        page = 1
        page_size = 100
        while capped_limit is None or len(type_rows) < capped_limit:
            remaining = capped_limit - len(type_rows) if capped_limit is not None else page_size
            result = await client.list_actresses(page=page, page_size=min(page_size, max(1, remaining)))
            items = result.get("data", []) if isinstance(result, dict) else []
            if not items:
                break
            for item in items:
                if not _append_metadata_row(type_rows, "actress", item, capped_limit):
                    break
            if not isinstance(result, dict):
                break
            total_pages = int(result.get("total_pages") or 0)
            if not total_pages:
                total_count = int(result.get("total_count") or 0)
                total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count else page
            if page >= total_pages:
                break
            page += 1
        rows.extend(type_rows)
    return rows


async def _translate_titles(job_id: int, items: list[dict], provider_order: list[str], counters: dict, *, force: bool) -> None:
    service = TranslatorService()
    for item in items:
        counters["processed"] += 1
        content_id = _content_id(item)
        source = _title_text(item)
        if not content_id or not source:
            counters["skipped"] += 1
            _progress(job_id, counters)
            continue
        scope = f"title:{content_id}:title_ja"
        if not force and get_cached_translation(scope, source):
            counters["skipped"] += 1
            _progress(job_id, counters)
            continue
        translated = await service.translate_text(
            source,
            scope=scope,
            context="video title",
            use_ai=False,
            persist_ai=True,
            provider_order=provider_order,
        )
        if translated and translated != source:
            upsert_translation(_normalize_code(content_id), {"title": {source: translated}})
            counters["translated"] += 1
        else:
            counters["failed"] += 1
        _progress(job_id, counters)


async def _translate_metadata_names(job_id: int, items: list[dict], provider_order: list[str], counters: dict, *, force: bool) -> None:
    service = TranslatorService()
    for item in items:
        counters["processed"] += 1
        entity_type = item.get("type")
        entity_id = item.get("id")
        source = str(item.get("text") or "").strip()
        if not entity_type or not entity_id or not source:
            counters["skipped"] += 1
            _progress(job_id, counters)
            continue
        scope = f"{entity_type}:{entity_id}"
        if not force and get_cached_translation(scope, source):
            counters["skipped"] += 1
            _progress(job_id, counters)
            continue
        translated = await service.translate_text(
            source,
            scope=scope,
            context=f"{entity_type} name",
            use_ai=False,
            persist_ai=True,
            provider_order=provider_order,
        )
        if translated and translated != source:
            upsert_translation(f"{entity_type}:{entity_id}", {entity_type: {source: translated}})
            counters["translated"] += 1
        else:
            counters["failed"] += 1
        _progress(job_id, counters)


def _progress(job_id: int, counters: dict) -> None:
    update_translation_job(
        job_id,
        processed=counters["processed"],
        translated=counters["translated"],
        skipped=counters["skipped"],
        failed=counters["failed"],
    )
