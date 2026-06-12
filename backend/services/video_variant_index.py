from __future__ import annotations

import asyncio
import copy
import getpass
import hashlib
import logging
import os
import re
from collections import defaultdict
from typing import Any, Iterable

from config import config
from database.video_variant_index import (
    add_variant_group_job,
    get_variant_group_by_content_ids,
    get_variant_group_job,
    replace_variant_groups,
    update_variant_group_job,
)
from services import cache
from services.video_variants import enrich_video_variants, is_non_movie_item

logger = logging.getLogger(__name__)

MAX_INDEXED_GROUP_ITEMS = 20


def scan_derived_video_rows(limit: int | None = None) -> Iterable[dict[str, Any]]:
    """Stream video rows from the JavInfo import database.

    Includes supplement-only rows from ``resolved_videos`` (data_origin =
    'supplement') when that table exists, so works that only live in the
    supplement layer participate in global variant grouping too.
    """
    conn = _connect_import_db()
    try:
        base_select = """
            SELECT content_id, dvd_id, title_ja, title_en, release_date, runtime_mins,
                   service_code, jacket_thumb_url
            FROM derived_video
            WHERE service_code IS NULL OR service_code <> 'ebook'
        """
        if _has_resolved_videos_table(conn):
            base_select = f"""
            SELECT * FROM (
                {base_select}
                UNION ALL
                SELECT rv.resolved_id AS content_id, rv.dvd_id, rv.title_ja, rv.title_en,
                       rv.release_date, rv.runtime_mins, rv.service_code, rv.jacket_thumb_url
                FROM resolved_videos rv
                WHERE rv.data_origin = 'supplement'
            ) combined
            """
        cursor = conn.cursor(name="javhub_variant_index_scan")
        cursor.itersize = 10000
        limit_clause = " LIMIT %s" if limit else ""
        params = (int(limit),) if limit else None
        cursor.execute(
            f"""
            {base_select}
            ORDER BY content_id
            {limit_clause}
            """,
            params,
        )
        try:
            for row in cursor:
                yield dict(row)
        finally:
            cursor.close()
    finally:
        conn.close()


def _has_resolved_videos_table(conn) -> bool:
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT to_regclass('resolved_videos') AS reg")
            row = cursor.fetchone()
            if row is None:
                return False
            value = row.get("reg") if isinstance(row, dict) else row[0]
            return value is not None
    except Exception as exc:  # noqa: BLE001 - absence must not break the job
        logger.warning("Could not check resolved_videos table: %s", exc)
        return False


def _connect_import_db():
    # Imported lazily so the pure grouping logic (build_variant_index_groups)
    # stays importable/testable without the postgres driver.
    import psycopg2
    from psycopg2.extras import RealDictCursor

    settings = config.javinfo_import_db
    attempts = [settings]
    current_user = getpass.getuser()
    if settings.get("user") != current_user:
        fallback = dict(settings)
        fallback["user"] = current_user
        fallback["password"] = os.getenv("PGPASSWORD", "")
        attempts.append(fallback)

    errors: list[str] = []
    for attempt in attempts:
        try:
            return psycopg2.connect(
                host=attempt["host"],
                port=int(attempt["port"]),
                dbname=attempt["database"],
                user=attempt["user"],
                password=attempt.get("password", ""),
                cursor_factory=RealDictCursor,
            )
        except Exception as exc:
            errors.append(f"user={attempt.get('user')}: {exc}")
    raise RuntimeError("Could not connect to JavInfo import database:\n" + "\n".join(errors))


def build_variant_index_groups(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build conservative multi-version groups from raw JavInfo rows.

    Bucketing uses the digit-stripped BASE canonical: store-digit editions
    (7UMSO-533 = 7net edition of UMSO-533) must land in the same bucket as the
    base code, otherwise the group-level adoption inside
    ``enrich_video_variants`` never sees both sides and the index would split
    what the actress page (which groups over the full collection) merges.
    """
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if is_non_movie_item(row):
            continue
        enriched = enrich_video_variants([row], variant_mode="flat", include_explanations=False)
        if not enriched:
            continue
        canonical = str(enriched[0].get("canonical_code") or "").strip()
        if canonical:
            buckets[_bucket_key(canonical)].append(row)

    groups: list[dict[str, Any]] = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        grouped = enrich_video_variants(bucket, variant_mode="grouped", include_explanations=False)
        for item in grouped:
            group_count = int(item.get("variant_group_count") or 1)
            group_items = item.get("variant_group_items") if isinstance(item.get("variant_group_items"), list) else []
            if group_count < 2 or len(group_items) < 2:
                continue
            # Use the (re-computed) canonical of the merged card, not the
            # bucket key — adoption may have rewritten digit-prefixed members
            # onto the base code.
            canonical_code = str(item.get("canonical_code") or "").strip() or "unknown"
            groups.append(_index_group_from_item(canonical_code, item, group_items))
    groups.sort(key=lambda group: str(group.get("group_id") or ""))
    return groups


_DIGIT_PREFIX_BUCKET_RE = re.compile(r"^\d([A-Z]{2,}-\d+[A-Z]*)$")


def _bucket_key(canonical: str) -> str:
    match = _DIGIT_PREFIX_BUCKET_RE.match(canonical)
    return match.group(1) if match else canonical


def hydrate_rows_with_actresses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    content_ids = [str(row.get("content_id") or "").strip() for row in rows if row.get("content_id")]
    if not content_ids:
        return rows
    actress_map = _load_actresses_for_content_ids(content_ids)
    if not actress_map:
        return rows
    hydrated = []
    for row in rows:
        copy_row = dict(row)
        actors = actress_map.get(str(row.get("content_id") or ""))
        if actors:
            copy_row["actresses"] = actors
        hydrated.append(copy_row)
    return hydrated


def apply_indexed_variant_groups(
    items: list[dict[str, Any]],
    *,
    include_explanations: bool = False,
    max_group_items: int = MAX_INDEXED_GROUP_ITEMS,
) -> list[dict[str, Any]]:
    """Inject materialized global variant groups into a page of enriched items."""
    if not items:
        return items
    content_ids = [str(item.get("content_id") or "").strip() for item in items if item.get("content_id")]
    if not content_ids:
        return items
    try:
        indexed = get_variant_group_by_content_ids(content_ids)
    except Exception as exc:
        logger.warning("Failed to read variant group index: %s", exc)
        return items
    if not indexed:
        return items

    result: list[dict[str, Any]] = []
    for item in items:
        content_id = str(item.get("content_id") or "").strip()
        group = indexed.get(content_id)
        if not group:
            row = copy.deepcopy(item)
            row.setdefault("variant_group_count", 1)
            row.setdefault("variant_group_items", [])
            result.append(row)
            continue

        row = copy.deepcopy(item)
        row["canonical_code"] = group.get("canonical_code") or row.get("canonical_code") or ""
        row["variant_group_count"] = int(group.get("group_count") or len(group.get("items") or []) or 1)
        row["variant_group_items"] = [
            _public_index_item(group_item, row["canonical_code"], include_explanations=include_explanations)
            for group_item in list(group.get("items") or [])[:max_group_items]
        ]
        row["variant_indexed"] = True
        result.append(row)
    return result


def start_variant_index_job() -> dict[str, Any]:
    job_id = add_variant_group_job("queued")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        run_variant_index_job(job_id)
    else:
        loop.create_task(asyncio.to_thread(run_variant_index_job, job_id))
    return get_variant_group_job(job_id) or {"id": job_id, "status": "queued"}


def run_variant_index_job(job_id: int, *, limit: int | None = None) -> dict[str, Any]:
    update_variant_group_job(job_id, status="running", processed=0, total=0)
    try:
        rows = list(scan_derived_video_rows() if limit is None else scan_derived_video_rows(limit=limit))
        rows = hydrate_rows_with_actresses(rows)
        update_variant_group_job(job_id, total=len(rows), processed=len(rows))
        groups = build_variant_index_groups(rows)
        result = replace_variant_groups(groups)
        cache.purge_response_cache()
        completed = update_variant_group_job(
            job_id,
            status="completed",
            total=len(rows),
            processed=len(rows),
            result=result,
            error="",
        )
        return {"status": "completed", **(completed or {}), "result": result}
    except Exception as exc:
        logger.exception("Variant index job %s failed", job_id)
        failed = update_variant_group_job(job_id, status="failed", error=str(exc))
        return {"status": "failed", **(failed or {}), "error": str(exc)}


def _index_group_from_item(canonical_code: str, item: dict[str, Any], group_items: list[dict[str, Any]]) -> dict[str, Any]:
    ordered_items = [_index_item(group_item, rank) for rank, group_item in enumerate(group_items)]
    primary = ordered_items[0] if ordered_items else {}
    return {
        "group_id": _group_id(canonical_code, ordered_items),
        "canonical_code": canonical_code,
        "primary_content_id": primary.get("content_id"),
        "group_count": len(ordered_items),
        "confidence": "high",
        "items": ordered_items,
    }


def _index_item(item: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "content_id": item.get("content_id"),
        "dvd_id": item.get("dvd_id"),
        "display_code": item.get("display_code") or item.get("dvd_id") or item.get("content_id"),
        "service_code": item.get("service_code"),
        "variant_labels": item.get("variant_labels") if isinstance(item.get("variant_labels"), list) else [],
        "sort_rank": rank,
    }


def _public_index_item(item: dict[str, Any], canonical_code: str, *, include_explanations: bool) -> dict[str, Any]:
    row = {
        "content_id": item.get("content_id"),
        "dvd_id": item.get("dvd_id"),
        "display_code": item.get("display_code") or item.get("dvd_id") or item.get("content_id") or "",
        "canonical_code": canonical_code,
        "service_code": item.get("service_code"),
        "variant_labels": item.get("variant_labels") if isinstance(item.get("variant_labels"), list) else [],
    }
    if include_explanations:
        row["variant_explanations"] = []
    return row


def _group_id(canonical_code: str, items: list[dict[str, Any]]) -> str:
    ids = "|".join(str(item.get("content_id") or item.get("dvd_id") or "") for item in items)
    digest = hashlib.sha1(ids.encode("utf-8")).hexdigest()[:12]
    normalized = "".join(ch.lower() for ch in canonical_code if ch.isalnum()) or "unknown"
    return f"vg:{normalized}:{digest}"


def _load_actresses_for_content_ids(content_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chunk_size = 1000
    try:
        conn = _connect_import_db()
    except Exception as exc:
        logger.warning("Failed to connect for variant actor hydration: %s", exc)
        return {}
    try:
        cursor = conn.cursor()
        for index in range(0, len(content_ids), chunk_size):
            chunk = content_ids[index:index + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            cursor.execute(
                f"""
                SELECT va.content_id, va.actress_id, a.name_kanji, a.name_romaji
                FROM derived_video_actress va
                LEFT JOIN derived_actress a ON a.id = va.actress_id
                WHERE va.content_id IN ({placeholders})
                ORDER BY va.content_id, va.ordinality
                """,
                chunk,
            )
            for row in cursor.fetchall():
                result[str(row["content_id"])].append(
                    {
                        "id": row.get("actress_id"),
                        "name_kanji": row.get("name_kanji"),
                        "name_romaji": row.get("name_romaji"),
                    }
                )
    except Exception as exc:
        logger.warning("Failed to hydrate variant index actresses: %s", exc)
        return {}
    finally:
        conn.close()
    return dict(result)
