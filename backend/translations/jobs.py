from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from config import config
from database import (
    add_translation_job,
    bulk_upsert_metadata_translations,
    bulk_upsert_title_translations,
    bulk_upsert_translation_workbench_items,
    get_translation,
    get_translation_job,
    list_translation_workbench_retry_batch,
    list_translation_jobs,
    mark_translation_workbench_failed,
    mark_translation_workbench_success,
    update_translation_job,
    upsert_translation,
)
from modules.info_client import get_info_client
from translations.providers import GoogleFreeProvider, TranslationRequest
from translations.service import TranslatorService

logger = logging.getLogger(__name__)

_running_jobs: dict[int, asyncio.Task] = {}
_paused_jobs: set[int] = set()

METADATA_ENTITY_TYPES = ("category", "series", "maker", "label", "actress")
METADATA_JOB_TYPES: dict[str, tuple[str, ...]] = {
    "metadata_names": METADATA_ENTITY_TYPES,
    "metadata_categories": ("category",),
    "metadata_series": ("series",),
    "metadata_makers": ("maker",),
    "metadata_labels": ("label",),
    "metadata_actresses": ("actress",),
}
WORKBENCH_RETRY_JOB_TYPE = "workbench_retry"
ALLOWED_JOB_TYPES = {"library_titles", *METADATA_JOB_TYPES.keys()}
JOB_MODES = {"remaining", "refresh_all"}
RETRYABLE_WORKBENCH_STATUSES = {"failed", "untranslated"}

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


def _batch_concurrency() -> int:
    return config.translation_batch_concurrency


def _batch_size() -> int:
    return config.translation_batch_size


def _batch_char_limit() -> int:
    return config.translation_batch_char_limit


def _source_page_size() -> int:
    return config.translation_source_page_size


def _scan_pages_per_batch() -> int:
    return config.translation_scan_pages_per_batch


def _active_provider_order(provider_order: list[str], *, force: bool) -> list[str]:
    if not force:
        return provider_order
    refreshed = [provider for provider in provider_order if provider not in {"cache", "mapping"}]
    return refreshed or provider_order


def _has_title_translation(content_id: str, source: str) -> bool:
    return bool(_title_known_translation(content_id, source).get("translated_text"))


def _has_metadata_translation(entity_type: str, entity_id: Any, source: str) -> bool:
    return bool(_metadata_known_translation(entity_type, entity_id, source).get("translated_text"))


def _title_known_translation(content_id: str, source: str) -> dict[str, Any]:
    if not content_id or not source:
        return {}
    for candidate in {_normalize_code(content_id), str(content_id or "").strip()}:
        if not candidate:
            continue
        raw = get_translation(candidate)
        mapping = raw.get("title", {}) if raw else {}
        translated = mapping.get(source) if isinstance(mapping, dict) else ""
        if translated:
            return {"translated_text": translated, "provider": "mapping", "model": None}
    return {}


def _metadata_known_translation(entity_type: str, entity_id: Any, source: str) -> dict[str, Any]:
    if not entity_type or not entity_id or not source:
        return {}
    raw = get_translation(f"{entity_type}:{entity_id}")
    mapping = raw.get(entity_type, {}) if raw else {}
    translated = mapping.get(source) if isinstance(mapping, dict) else ""
    if translated:
        return {"translated_text": translated, "provider": "mapping", "model": None}
    return {}


def _network_provider_order(provider_order: list[str]) -> list[str]:
    return [provider for provider in provider_order if provider not in {"cache", "mapping"}]


def _can_batch_google(provider_order: list[str]) -> bool:
    return bool(_network_provider_order(provider_order)[:1] == ["google_free"])


def _job_resume_page(current_job_id: int, job_type: str, mode: str) -> int:
    if mode != "remaining" or job_type != "library_titles":
        return 1
    for job in list_translation_jobs(limit=100):
        if not job or job.get("id") == current_job_id or job.get("job_type") != job_type:
            continue
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        if result.get("mode") == "refresh_all":
            continue
        try:
            next_page = int(result.get("next_page") or 0)
        except Exception:
            next_page = 0
        if next_page > 1:
            return next_page
        try:
            legacy_limit = int(result.get("limit") or 0)
            processed = int(job.get("processed") or result.get("processed") or 0)
        except Exception:
            legacy_limit = 0
            processed = 0
        if legacy_limit > 0 and processed >= legacy_limit:
            return max(1, processed // 100 + 1)
    return 1


async def create_translation_job(
    job_type: str = "library_titles",
    *,
    provider_order: list[str] | None = None,
    mode: str = "remaining",
    force: bool | None = None,
) -> dict:
    if job_type not in ALLOWED_JOB_TYPES:
        raise ValueError(f"job_type must be one of: {', '.join(sorted(ALLOWED_JOB_TYPES))}")
    if force is not None:
        mode = "refresh_all" if force else "remaining"
    if mode not in JOB_MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(JOB_MODES))}")
    order = _batch_order(provider_order)
    job_id = add_translation_job(job_type, scope="library", provider_order=order)
    task = asyncio.create_task(_run_job(job_id, job_type, order, mode=mode))
    _running_jobs[job_id] = task
    task.add_done_callback(lambda _: _running_jobs.pop(job_id, None))
    return get_translation_job(job_id) or {"id": job_id, "status": "pending"}


async def create_translation_retry_job(
    *,
    item_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    ids: list[str] | None = None,
    provider_order: list[str] | None = None,
) -> dict:
    if item_type and item_type not in {"title", *METADATA_ENTITY_TYPES}:
        raise ValueError("type must be one of: title, actress, category, series, maker, label")
    if status and status not in {"untranslated", "machine_translated", "reviewed", "manual_edited", "failed", "invalid"}:
        raise ValueError("status is not valid")
    order = _batch_order(provider_order)
    job_id = add_translation_job(WORKBENCH_RETRY_JOB_TYPE, scope=item_type or "workbench", provider_order=order)
    task = asyncio.create_task(
        _run_workbench_retry_job(
            job_id,
            order,
            item_type=item_type,
            status=status,
            q=q,
            ids=ids,
        )
    )
    _running_jobs[job_id] = task
    task.add_done_callback(lambda _: _running_jobs.pop(job_id, None))
    return get_translation_job(job_id) or {"id": job_id, "status": "pending"}


def list_jobs(limit: int = 50) -> list[dict]:
    jobs = list_translation_jobs(limit=limit)
    return [_normalize_job_runtime_state(job) for job in jobs]


def get_job(job_id: int) -> dict | None:
    job = get_translation_job(job_id)
    return _normalize_job_runtime_state(job) if job else None


def _normalize_job_runtime_state(job: dict | None) -> dict | None:
    if not job:
        return None
    job_id = int(job.get("id") or 0)
    running = job_id in _running_jobs
    if job.get("status") in {"pending", "running"} and not running:
        now = datetime.utcnow().isoformat(timespec="seconds")
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        update_translation_job(
            job_id,
            status="paused",
            finished_at=now,
            result={**result, "paused": True, "orphaned": True},
        )
        job = get_translation_job(job_id) or job
        running = False
    job["running"] = running
    return job


def pause_translation_job(job_id: int) -> dict | None:
    job = get_translation_job(job_id)
    if not job:
        return None
    if job.get("status") not in {"pending", "running"}:
        return job

    _paused_jobs.add(job_id)
    task = _running_jobs.get(job_id)
    now = datetime.utcnow().isoformat(timespec="seconds")
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    update_translation_job(
        job_id,
        status="paused",
        finished_at=now,
        result={**result, "paused": True, "pause_requested_at": now},
    )
    if task and not task.done():
        task.cancel()
    return get_translation_job(job_id)


async def _run_job(
    job_id: int,
    job_type: str,
    provider_order: list[str],
    *,
    mode: str = "remaining",
    force: bool | None = None,
    limit: int | None = None,
) -> None:
    if force is not None:
        mode = "refresh_all" if force else "remaining"
    force_refresh = mode == "refresh_all"
    counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
    resume_page = _job_resume_page(job_id, job_type, mode)
    result_state = {"provider_order": provider_order, "mode": mode}
    if resume_page > 1:
        result_state["resume_from_page"] = resume_page
        result_state["next_page"] = resume_page
    update_translation_job(
        job_id,
        status="running",
        started_at=datetime.utcnow().isoformat(timespec="seconds"),
        result=result_state,
    )
    try:
        failed_processed = await _retry_failed_workbench_items(job_id, job_type, provider_order, counters, force=force_refresh)
        if failed_processed:
            result_state["failed_retry_processed"] = failed_processed
            update_translation_job(job_id, result={**result_state, **counters})
        if job_type == "library_titles":
            await _translate_library_titles_pages(
                job_id,
                provider_order,
                counters,
                force=force_refresh,
                start_page=resume_page,
                result_state=result_state,
            )
            if not force_refresh and resume_page > 1:
                result_state["sweep_before_page"] = resume_page
                await _translate_library_titles_pages(
                    job_id,
                    provider_order,
                    counters,
                    force=False,
                    start_page=1,
                    end_before_page=resume_page,
                    result_state=result_state,
                    update_total=False,
                    cursor_prefix="sweep_",
                )
        elif job_type in METADATA_JOB_TYPES:
            items = await _collect_metadata_names(METADATA_JOB_TYPES[job_type])
            update_translation_job(job_id, total=len(items))
            await _translate_metadata_names(job_id, items, provider_order, counters, force=force_refresh)
        if job_id in _paused_jobs:
            raise asyncio.CancelledError()
        update_translation_job(
            job_id,
            status="completed",
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters},
        )
    except asyncio.CancelledError:
        logger.info("Translation job %s paused", job_id)
        _paused_jobs.discard(job_id)
        update_translation_job(
            job_id,
            status="paused",
            error_msg=None,
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters, "paused": True},
        )
    except Exception as exc:
        logger.exception("Translation job %s failed", job_id)
        _paused_jobs.discard(job_id)
        update_translation_job(
            job_id,
            status="failed",
            error_msg=str(exc),
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters},
        )


async def _run_workbench_retry_job(
    job_id: int,
    provider_order: list[str],
    *,
    item_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    ids: list[str] | None = None,
) -> None:
    counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
    retry_statuses = [status] if status in RETRYABLE_WORKBENCH_STATUSES else sorted(RETRYABLE_WORKBENCH_STATUSES)
    item_types = (item_type,) if item_type else ("title", *METADATA_ENTITY_TYPES)
    result_state = {
        "provider_order": provider_order,
        "filters": {"type": item_type, "status": status, "q": q, "ids": ids or []},
        "retry_statuses": retry_statuses,
    }
    update_translation_job(
        job_id,
        status="running",
        started_at=datetime.utcnow().isoformat(timespec="seconds"),
        result=result_state,
    )
    try:
        total_seen = 0
        for current_type in item_types:
            after_row_id = 0
            while True:
                batch = list_translation_workbench_retry_batch(
                    item_type=current_type,
                    statuses=retry_statuses,
                    q=q,
                    ids=ids,
                    after_row_id=after_row_id,
                    limit=1000,
                )
                if not batch:
                    break
                after_row_id = max(int(item.get("row_id") or 0) for item in batch)
                total_seen += len(batch)
                update_translation_job(job_id, total=total_seen)
                await _translate_workbench_items(job_id, batch, provider_order, counters, force=True)
                update_translation_job(job_id, result={**result_state, **counters})
        if job_id in _paused_jobs:
            raise asyncio.CancelledError()
        update_translation_job(
            job_id,
            status="completed",
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters},
        )
    except asyncio.CancelledError:
        logger.info("Translation retry job %s paused", job_id)
        _paused_jobs.discard(job_id)
        update_translation_job(
            job_id,
            status="paused",
            error_msg=None,
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters, "paused": True},
        )
    except Exception as exc:
        logger.exception("Translation retry job %s failed", job_id)
        _paused_jobs.discard(job_id)
        update_translation_job(
            job_id,
            status="failed",
            error_msg=str(exc),
            finished_at=datetime.utcnow().isoformat(timespec="seconds"),
            result={**result_state, **counters},
        )


def _job_workbench_types(job_type: str) -> tuple[str, ...]:
    if job_type == "library_titles":
        return ("title",)
    if job_type in METADATA_JOB_TYPES:
        return METADATA_JOB_TYPES[job_type]
    return ()


async def _retry_failed_workbench_items(
    job_id: int,
    job_type: str,
    provider_order: list[str],
    counters: dict,
    *,
    force: bool,
) -> int:
    if force:
        return 0
    processed = 0
    for item_type in _job_workbench_types(job_type):
        after_row_id = 0
        while True:
            batch = list_translation_workbench_retry_batch(
                item_type=item_type,
                statuses=["failed"],
                after_row_id=after_row_id,
                limit=1000,
            )
            if not batch:
                break
            after_row_id = max(int(item.get("row_id") or 0) for item in batch)
            processed += len(batch)
            await _translate_workbench_items(job_id, batch, provider_order, counters, force=False)
    return processed


async def _translate_workbench_items(
    job_id: int,
    items: list[dict],
    provider_order: list[str],
    counters: dict,
    *,
    force: bool,
) -> None:
    title_items = [
        {
            "content_id": item.get("item_id"),
            "title_ja": item.get("source_text"),
            "_translation_scope": item.get("scope"),
        }
        for item in items
        if item.get("item_type") == "title"
    ]
    metadata_items = [
        {
            "type": item.get("item_type"),
            "id": item.get("item_id"),
            "text": item.get("source_text"),
            "_translation_scope": item.get("scope"),
        }
        for item in items
        if item.get("item_type") in METADATA_ENTITY_TYPES
    ]
    if title_items:
        await _translate_titles(job_id, title_items, provider_order, counters, force=force)
    if metadata_items:
        await _translate_metadata_names(job_id, metadata_items, provider_order, counters, force=force)


async def _translate_library_titles_pages(
    job_id: int,
    provider_order: list[str],
    counters: dict,
    *,
    force: bool,
    start_page: int = 1,
    end_before_page: int | None = None,
    result_state: dict | None = None,
    update_total: bool = True,
    cursor_prefix: str = "",
) -> None:
    client = get_info_client()
    page = max(1, int(start_page or 1))
    page_size = _source_page_size()
    pages_per_batch = _scan_pages_per_batch()
    total_known = not update_total
    total_pages: int | None = None
    state = result_state if result_state is not None else {}
    while True:
        if end_before_page is not None and page >= max(1, int(end_before_page)):
            break

        first_result = await client.list_videos(page=page, page_size=page_size)
        if not isinstance(first_result, dict):
            break
        if total_pages is None:
            raw_total_pages = int(first_result.get("total_pages") or 0)
            if raw_total_pages:
                total_pages = raw_total_pages
            else:
                total_count = int(first_result.get("total_count") or 0)
                if total_count:
                    total_pages = max(1, (total_count + page_size - 1) // page_size)

        batch_end = page + pages_per_batch
        if end_before_page is not None:
            batch_end = min(batch_end, max(1, int(end_before_page)))
        if total_pages:
            batch_end = min(batch_end, total_pages + 1)
        pages = list(range(page, batch_end))
        if not pages:
            break

        extra_pages = pages[1:]
        extra_results = await asyncio.gather(
            *(client.list_videos(page=current_page, page_size=page_size) for current_page in extra_pages)
        ) if extra_pages else []
        results = [first_result, *extra_results]
        batch_items: list[dict] = []
        last_page_with_items = 0
        for current_page, result in zip(pages, results):
            if not isinstance(result, dict):
                continue
            if total_pages is None:
                raw_total_pages = int(result.get("total_pages") or 0)
                if raw_total_pages:
                    total_pages = raw_total_pages
                else:
                    total_count = int(result.get("total_count") or 0)
                    if total_count:
                        total_pages = max(1, (total_count + page_size - 1) // page_size)
            page_items = result.get("data", []) if isinstance(result, dict) else []
            if not page_items:
                continue
            last_page_with_items = current_page
            for item in page_items:
                if isinstance(item, dict):
                    batch_items.append({**item, "_source_page": current_page})

        if not batch_items:
            break
        if not total_known:
            total_count = int(first_result.get("total_count") or 0)
            if total_count:
                remaining_total = max(total_count - ((page - 1) * page_size), len(batch_items))
                update_translation_job(job_id, total=remaining_total)
                state["source_total_count"] = total_count
                total_known = True
        await _translate_titles(job_id, batch_items, provider_order, counters, force=force)
        last_page = last_page_with_items or pages[-1]
        state[f"{cursor_prefix}last_page"] = last_page
        state[f"{cursor_prefix}next_page"] = last_page + 1
        update_translation_job(job_id, result={**state, **counters})
        if total_pages and last_page >= total_pages:
            break
        page = last_page + 1
    if update_total and not total_known:
        update_translation_job(job_id, total=counters["processed"])


async def _collect_library_titles(limit: int | None = None) -> list[dict]:
    client = get_info_client()
    items: list[dict] = []
    page = 1
    page_size = 100 if limit is None else min(max(limit, 1), 100)
    while limit is None or len(items) < limit:
        requested = page_size if limit is None else min(page_size, limit - len(items))
        result = await client.list_videos(page=page, page_size=requested)
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


async def _translate_titles(
    job_id: int,
    items: list[dict],
    provider_order: list[str],
    counters: dict,
    *,
    force: bool,
    source_page: int | None = None,
) -> None:
    active_provider_order = _active_provider_order(provider_order, force=force)
    pending: list[dict] = []
    index_entries: list[dict] = []
    skipped = 0
    for item in items:
        content_id = _content_id(item)
        source = _title_text(item)
        if not content_id or not source:
            skipped += 1
            continue
        scope = str(item.get("_translation_scope") or f"title:{content_id}:title_ja")
        known = _title_known_translation(content_id, source)
        item_source_page = item.get("_source_page", source_page)
        index_entries.append({
            "item_type": "title",
            "item_id": _normalize_code(content_id),
            "source_text": source,
            "translated_text": known.get("translated_text") or "",
            "status": "machine_translated" if known.get("translated_text") else "untranslated",
            "provider": known.get("provider"),
            "model": known.get("model"),
            "source_page": item_source_page,
            "scope": scope,
        })
        if not force and known.get("translated_text"):
            skipped += 1
            continue
        pending.append({
            "item_type": "title",
            "item_id": _normalize_code(content_id),
            "content_id": content_id,
            "source": source,
            "source_text": source,
            "scope": scope,
            "source_page": item_source_page,
        })

    if index_entries:
        bulk_upsert_translation_workbench_items(index_entries)
    if skipped:
        _record_many(job_id, counters, processed=skipped, skipped=skipped)
    if not pending:
        return
    if _can_batch_google(active_provider_order):
        await _translate_title_batches_with_google(job_id, pending, counters, preserve_reviewed=not force)
        return

    network_provider_order = _network_provider_order(active_provider_order)
    if not network_provider_order:
        mark_translation_workbench_failed([{**item, "last_error": "no network translation provider"} for item in pending])
        _record_many(job_id, counters, processed=len(pending), failed=len(pending))
        return

    service = TranslatorService(reuse_clients=True)
    semaphore = asyncio.Semaphore(_batch_concurrency())
    lock = asyncio.Lock()

    async def record(field: str) -> None:
        async with lock:
            counters["processed"] += 1
            counters[field] += 1
            _progress(job_id, counters)

    async def translate_one(item: dict) -> None:
        content_id = item["content_id"]
        source = item["source"]
        scope = item["scope"]
        try:
            async with semaphore:
                translated = await service.translate_text(
                    source,
                    scope=scope,
                    context="video title",
                    use_ai=False,
                    persist_ai=False,
                    provider_order=network_provider_order,
                    return_original=False,
                )
        except Exception:
            logger.exception("Title translation failed for %s", content_id)
            mark_translation_workbench_failed([{**item, "last_error": "translation failed"}])
            await record("failed")
            return
        if translated:
            upsert_translation(_normalize_code(content_id), {"title": {source: translated}})
            mark_translation_workbench_success(
                [{
                    **item,
                    "translated_text": translated,
                    "provider": "translation_service",
                    "model": None,
                }],
                preserve_reviewed=not force,
            )
            await record("translated")
        else:
            mark_translation_workbench_failed([{**item, "last_error": "translation returned empty"}])
            await record("failed")

    try:
        await asyncio.gather(*(translate_one(item) for item in pending))
    finally:
        await service.close()


async def _translate_metadata_names(job_id: int, items: list[dict], provider_order: list[str], counters: dict, *, force: bool) -> None:
    active_provider_order = _active_provider_order(provider_order, force=force)
    pending: list[dict] = []
    index_entries: list[dict] = []
    skipped = 0
    for item in items:
        entity_type = item.get("type")
        entity_id = item.get("id")
        source = str(item.get("text") or "").strip()
        if not entity_type or not entity_id or not source:
            skipped += 1
            continue
        scope = str(item.get("_translation_scope") or f"{entity_type}:{entity_id}")
        known = _metadata_known_translation(str(entity_type), entity_id, source)
        index_entries.append({
            "item_type": str(entity_type),
            "item_id": str(entity_id),
            "source_text": source,
            "translated_text": known.get("translated_text") or "",
            "status": "machine_translated" if known.get("translated_text") else "untranslated",
            "provider": known.get("provider"),
            "model": known.get("model"),
            "scope": scope,
        })
        if not force and known.get("translated_text"):
            skipped += 1
            continue
        pending.append({
            "item_type": str(entity_type),
            "item_id": str(entity_id),
            "type": entity_type,
            "id": entity_id,
            "source": source,
            "source_text": source,
            "scope": scope,
        })

    if index_entries:
        bulk_upsert_translation_workbench_items(index_entries)
    if skipped:
        _record_many(job_id, counters, processed=skipped, skipped=skipped)
    if not pending:
        return
    if _can_batch_google(active_provider_order):
        await _translate_metadata_batches_with_google(job_id, pending, counters, preserve_reviewed=not force)
        return

    network_provider_order = _network_provider_order(active_provider_order)
    if not network_provider_order:
        mark_translation_workbench_failed([{**item, "last_error": "no network translation provider"} for item in pending])
        _record_many(job_id, counters, processed=len(pending), failed=len(pending))
        return

    service = TranslatorService(reuse_clients=True)
    semaphore = asyncio.Semaphore(_batch_concurrency())
    lock = asyncio.Lock()

    async def record(field: str) -> None:
        async with lock:
            counters["processed"] += 1
            counters[field] += 1
            _progress(job_id, counters)

    async def translate_one(item: dict) -> None:
        entity_type = item["type"]
        entity_id = item["id"]
        source = item["source"]
        scope = item["scope"]
        try:
            async with semaphore:
                translated = await service.translate_text(
                    source,
                    scope=scope,
                    context=f"{entity_type} name",
                    use_ai=False,
                    persist_ai=False,
                    provider_order=network_provider_order,
                    return_original=False,
                )
        except Exception:
            logger.exception("Metadata translation failed for %s:%s", entity_type, entity_id)
            mark_translation_workbench_failed([{**item, "last_error": "translation failed"}])
            await record("failed")
            return
        if translated:
            upsert_translation(f"{entity_type}:{entity_id}", {entity_type: {source: translated}})
            mark_translation_workbench_success(
                [{
                    **item,
                    "translated_text": translated,
                    "provider": "translation_service",
                    "model": None,
                }],
                preserve_reviewed=not force,
            )
            await record("translated")
        else:
            mark_translation_workbench_failed([{**item, "last_error": "translation returned empty"}])
            await record("failed")

    try:
        await asyncio.gather(*(translate_one(item) for item in pending))
    finally:
        await service.close()


def _translation_chunks(items: list[dict]) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    chunk: list[dict] = []
    char_count = 0
    size_limit = _batch_size()
    char_limit = _batch_char_limit()
    for item in items:
        text_len = max(1, len(str(item.get("source") or "")))
        if chunk and (len(chunk) >= size_limit or char_count + text_len > char_limit):
            chunks.append(chunk)
            chunk = []
            char_count = 0
        chunk.append(item)
        char_count += text_len
    if chunk:
        chunks.append(chunk)
    return chunks


async def _translate_title_batches_with_google(
    job_id: int,
    pending: list[dict],
    counters: dict,
    *,
    preserve_reviewed: bool = True,
) -> None:
    provider = GoogleFreeProvider(config.translation.get("google_free", {}) or {}, reuse_client=True)
    semaphore = asyncio.Semaphore(_batch_concurrency())
    lock = asyncio.Lock()

    async def translate_chunk(chunk: list[dict]) -> None:
        requests = [
            TranslationRequest(
                text=item["source"],
                scope=item["scope"],
                target_language=config.translation_target_language,
                context="video title",
            )
            for item in chunk
        ]
        batch_error = "translation returned empty"
        try:
            async with semaphore:
                results = await provider.translate_many(requests)
        except Exception as exc:
            logger.exception("Title batch translation failed for %s items", len(chunk))
            batch_error = str(exc)
            results = [None for _ in chunk]

        title_entries = []
        workbench_success = []
        workbench_failed = []
        translated = 0
        failed = 0
        for item, result in zip(chunk, results):
            if result and result.translated_text:
                text = result.translated_text.strip()
                title_entries.append((item["content_id"], item["source"], text))
                workbench_success.append({
                    **item,
                    "translated_text": text,
                    "provider": result.provider,
                    "model": result.model,
                })
                translated += 1
            else:
                workbench_failed.append({**item, "last_error": batch_error})
                failed += 1
        bulk_upsert_title_translations(title_entries)
        mark_translation_workbench_success(workbench_success, preserve_reviewed=preserve_reviewed)
        mark_translation_workbench_failed(workbench_failed)
        async with lock:
            _record_many(job_id, counters, processed=len(chunk), translated=translated, failed=failed)

    try:
        await asyncio.gather(*(translate_chunk(chunk) for chunk in _translation_chunks(pending)))
    finally:
        await provider.aclose()


async def _translate_metadata_batches_with_google(
    job_id: int,
    pending: list[dict],
    counters: dict,
    *,
    preserve_reviewed: bool = True,
) -> None:
    provider = GoogleFreeProvider(config.translation.get("google_free", {}) or {}, reuse_client=True)
    semaphore = asyncio.Semaphore(_batch_concurrency())
    lock = asyncio.Lock()

    async def translate_chunk(chunk: list[dict]) -> None:
        requests = [
            TranslationRequest(
                text=item["source"],
                scope=item["scope"],
                target_language=config.translation_target_language,
                context=f"{item['type']} name",
            )
            for item in chunk
        ]
        batch_error = "translation returned empty"
        try:
            async with semaphore:
                results = await provider.translate_many(requests)
        except Exception as exc:
            logger.exception("Metadata batch translation failed for %s items", len(chunk))
            batch_error = str(exc)
            results = [None for _ in chunk]

        metadata_entries = []
        workbench_success = []
        workbench_failed = []
        translated = 0
        failed = 0
        for item, result in zip(chunk, results):
            if result and result.translated_text:
                text = result.translated_text.strip()
                metadata_entries.append((str(item["type"]), str(item["id"]), item["source"], text))
                workbench_success.append({
                    **item,
                    "translated_text": text,
                    "provider": result.provider,
                    "model": result.model,
                })
                translated += 1
            else:
                workbench_failed.append({**item, "last_error": batch_error})
                failed += 1
        bulk_upsert_metadata_translations(metadata_entries)
        mark_translation_workbench_success(workbench_success, preserve_reviewed=preserve_reviewed)
        mark_translation_workbench_failed(workbench_failed)
        async with lock:
            _record_many(job_id, counters, processed=len(chunk), translated=translated, failed=failed)

    try:
        await asyncio.gather(*(translate_chunk(chunk) for chunk in _translation_chunks(pending)))
    finally:
        await provider.aclose()


def _record_many(
    job_id: int,
    counters: dict,
    *,
    processed: int = 0,
    translated: int = 0,
    skipped: int = 0,
    failed: int = 0,
) -> None:
    counters["processed"] += processed
    counters["translated"] += translated
    counters["skipped"] += skipped
    counters["failed"] += failed
    _progress(job_id, counters)


def _progress(job_id: int, counters: dict) -> None:
    update_translation_job(
        job_id,
        processed=counters["processed"],
        translated=counters["translated"],
        skipped=counters["skipped"],
        failed=counters["failed"],
    )
