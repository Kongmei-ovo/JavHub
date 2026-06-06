"""Download candidate database layer."""
from __future__ import annotations

import json
import time
from typing import Optional

from database.base import get_db


VALID_CANDIDATE_STATUSES = {"candidate", "approved", "rejected", "sent", "failed"}
_DOWNLOAD_CANDIDATE_ORDER_TERMS = """
    CASE status
        WHEN 'candidate' THEN 0
        WHEN 'approved' THEN 1
        WHEN 'failed' THEN 2
        WHEN 'sent' THEN 3
        ELSE 4
    END,
    release_date DESC,
    created_at ASC,
    id ASC
"""
_DOWNLOAD_CANDIDATE_ORDER_BY = f"ORDER BY {_DOWNLOAD_CANDIDATE_ORDER_TERMS}"
_SUMMARY_KEYS = ("total", "candidate", "approved", "rejected", "sent", "failed", "needs_magnet", "ready")


def _bump_download_candidate_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("download_candidates", time.time_ns())
    except Exception:
        pass


def candidate_content_id(video: dict) -> str:
    """Pick the stable local candidate key from a JavInfo video item."""
    return str(
        video.get("content_id")
        or video.get("dvd_id")
        or video.get("canonical_number")
        or video.get("id")
        or ""
    ).strip()


def candidate_title(video: dict) -> str:
    return str(video.get("title_ja") or video.get("title_en") or video.get("title") or "").strip()


def upsert_download_candidate(
    content_id: str,
    dvd_id: str | None = None,
    title: str | None = None,
    actress_id: int | None = None,
    actress_name: str | None = None,
    jacket_thumb_url: str | None = None,
    release_date: str | None = None,
    source: str = "manual",
    reason: str | None = None,
    status: str = "candidate",
    magnet: str | None = None,
    magnet_source: str | None = None,
    return_insert_status: bool = False,
) -> dict:
    """Insert or refresh a candidate, preserving manual decisions."""
    if status not in VALID_CANDIDATE_STATUSES:
        raise ValueError(f"invalid download candidate status: {status}")
    content_id = str(content_id or "").strip()
    if not content_id:
        raise ValueError("content_id is required")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO download_candidates (
                content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url,
                release_date, source, reason, status, magnet, magnet_source,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id, source) DO NOTHING
            RETURNING id
            ''',
            (
                content_id,
                dvd_id,
                title,
                actress_id,
                actress_name,
                jacket_thumb_url,
                release_date,
                source,
                reason,
                status,
                magnet,
                magnet_source,
            ),
        )
        inserted = cursor.fetchone()
        was_inserted = inserted is not None
        if not was_inserted:
            cursor.execute(
                '''
                UPDATE download_candidates
                SET
                    dvd_id = COALESCE(?, dvd_id),
                    title = COALESCE(?, title),
                    actress_id = COALESCE(?, actress_id),
                    actress_name = COALESCE(?, actress_name),
                    jacket_thumb_url = COALESCE(?, jacket_thumb_url),
                    release_date = COALESCE(?, release_date),
                    reason = COALESCE(?, reason),
                    status = CASE
                        WHEN status IN ('rejected', 'sent', 'failed') THEN status
                        ELSE ?
                    END,
                    magnet = COALESCE(magnet, ?),
                    magnet_source = COALESCE(magnet_source, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE content_id = ? AND source = ?
                ''',
                (
                    dvd_id,
                    title,
                    actress_id,
                    actress_name,
                    jacket_thumb_url,
                    release_date,
                    reason,
                    status,
                    magnet,
                    magnet_source,
                    content_id,
                    source,
                ),
            )
        cursor.execute(
            "SELECT * FROM download_candidates WHERE content_id = ? AND source = ?",
            (content_id, source),
        )
        row = dict(cursor.fetchone())
        _bump_download_candidate_generation()
        if return_insert_status:
            row["was_inserted"] = was_inserted
        return row


def upsert_candidate_from_video(
    video: dict,
    actress_id: int | None,
    actress_name: str | None,
    source: str,
    reason: str,
    return_insert_status: bool = False,
) -> dict:
    content_id = candidate_content_id(video)
    dvd_id = video.get("dvd_id") or content_id
    return upsert_download_candidate(
        content_id=content_id,
        dvd_id=dvd_id,
        title=candidate_title(video),
        actress_id=actress_id,
        actress_name=actress_name,
        jacket_thumb_url=video.get("jacket_thumb_url") or video.get("jacket_full_url"),
        release_date=video.get("release_date"),
        source=source,
        reason=reason,
        return_insert_status=return_insert_status,
    )


def _enrich_candidate_rows_with_cursor(rows: list[dict], cursor) -> list[dict]:
    task_ids = sorted({row.get("download_task_id") for row in rows if row.get("download_task_id")})
    tasks = {}
    if task_ids:
        placeholders = ",".join("?" for _ in task_ids)
        cursor.execute(
            f"SELECT id, status, error_msg, path, downloader_id, downloader_name, downloader_type, created_at, updated_at FROM download_tasks WHERE id IN ({placeholders})",
            task_ids,
        )
        tasks = {row["id"]: dict(row) for row in cursor.fetchall()}
    candidate_ids = sorted({row.get("id") for row in rows if row.get("id")})
    latest_events = {}
    if candidate_ids:
        event_placeholders = ",".join("?" for _ in candidate_ids)
        cursor.execute(
            f'''
            SELECT e.*
            FROM download_candidate_events e
            JOIN (
                SELECT candidate_id, MAX(id) AS max_id
                FROM download_candidate_events
                WHERE candidate_id IN ({event_placeholders})
                GROUP BY candidate_id
            ) latest ON latest.max_id = e.id
            ''',
            candidate_ids,
        )
        latest_events = {row["candidate_id"]: dict(row) for row in cursor.fetchall()}
    for row in rows:
        task_id = row.get("download_task_id")
        if task_id and task_id in tasks:
            row["download_task"] = tasks[task_id]
        latest = latest_events.get(row.get("id"))
        if latest:
            row["latest_event"] = latest
            row["events"] = [latest]
    return rows


def _enrich_candidate_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return rows
    with get_db() as conn:
        cursor = conn.cursor()
        return _enrich_candidate_rows_with_cursor(rows, cursor)


def add_download_candidate_event(
    candidate_id: int,
    action: str,
    detail: str | None = None,
    operator: str = "system",
) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO download_candidate_events (candidate_id, action, detail, operator, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (candidate_id, action, detail, operator),
        )
        event_id = cursor.lastrowid
        _bump_download_candidate_generation()
        return event_id


def list_download_candidate_events(candidate_id: int, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM download_candidate_events
            WHERE candidate_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            ''',
            (candidate_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def list_download_candidates(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        where_clause, params = _candidate_filter_clause(
            status=status,
            actress_id=actress_id,
            source=source,
            q=q,
            needs_magnet=needs_magnet,
            missing_cover=missing_cover,
            latest_event_action=latest_event_action,
        )
        cursor.execute(
            f'''
            SELECT * FROM download_candidates
            {where_clause}
            {_DOWNLOAD_CANDIDATE_ORDER_BY}
            LIMIT ? OFFSET ?
            ''',
            params + [limit, offset],
        )
        rows = [dict(row) for row in cursor.fetchall()]
    return _enrich_candidate_rows(rows)


def download_candidate_content_keys(
    actress_id: int | None = None,
    source: str | None = None,
) -> set[tuple[str, str]]:
    where = []
    params: list = []
    if actress_id is not None:
        where.append("actress_id = ?")
        params.append(actress_id)
    if source:
        where.append("source = ?")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT content_id, source
            FROM download_candidates
            {where_clause}
            ''',
            params,
        )
        return {
            (row["content_id"], row["source"])
            for row in cursor.fetchall()
            if row.get("content_id") and row.get("source")
        }


def list_download_candidates_page(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
    limit: int = 200,
    offset: int = 0,
    include_stats: bool = False,
) -> dict:
    limit = max(1, int(limit or 200))
    offset = max(0, int(offset or 0))
    where_clause, params = _candidate_filter_clause(
        status=status,
        actress_id=actress_id,
        source=source,
        q=q,
        needs_magnet=needs_magnet,
        missing_cover=missing_cover,
        latest_event_action=latest_event_action,
        table_ref="c",
    )
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT c.*, COUNT(*) OVER() AS __filtered_total
            FROM download_candidates c
            {where_clause}
            {_DOWNLOAD_CANDIDATE_ORDER_BY}
            LIMIT ? OFFSET ?
            ''',
            params + [limit, offset],
        )
        result_rows = [dict(row) for row in cursor.fetchall()]
        total = int(result_rows[0].pop("__filtered_total", 0) or 0) if result_rows else 0
        for row in result_rows[1:]:
            row.pop("__filtered_total", None)
        if not result_rows:
            cursor.execute(
                f'''
                SELECT COUNT(*) AS total
                FROM download_candidates c
                {where_clause}
                ''',
                params,
            )
            total_row = cursor.fetchone()
            total = int(total_row["total"] if total_row else 0)
        rows = _enrich_candidate_rows_with_cursor(result_rows, cursor)
        result = {"data": rows, "total": total}
        if include_stats:
            result["stats"] = _download_candidate_stats_with_cursor(cursor)
    return result


def download_candidate_counts_by_actress(
    status: str = "candidate",
    source: str = "subscription",
) -> dict[int, dict[str, int]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                actress_id,
                COUNT(*) AS candidate_count,
                SUM(CASE WHEN magnet IS NULL OR magnet = '' THEN 1 ELSE 0 END) AS needs_magnet_count
            FROM download_candidates
            WHERE status = ? AND source = ? AND actress_id IS NOT NULL
            GROUP BY actress_id
            ''',
            (status, source),
        )
        return {
            int(row["actress_id"]): {
                "candidate_count": int(row["candidate_count"] or 0),
                "needs_magnet_count": int(row["needs_magnet_count"] or 0),
            }
            for row in cursor.fetchall()
        }


def list_download_candidates_by_actress_ids(
    actress_ids: list[int],
    status: str = "candidate",
    source: str = "subscription",
    limit_per_actress: int = 100,
) -> dict[int, list[dict]]:
    ids = sorted({int(actress_id) for actress_id in actress_ids if actress_id})
    if not ids:
        return {}
    limit_per_actress = max(1, int(limit_per_actress or 100))
    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT *
            FROM (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY actress_id
                        ORDER BY {_DOWNLOAD_CANDIDATE_ORDER_TERMS}
                    ) AS __rn
                FROM download_candidates c
                WHERE status = ? AND source = ? AND actress_id IN ({placeholders})
            ) ranked
            WHERE __rn <= ?
            ORDER BY actress_id, __rn
            ''',
            [status, source, *ids, limit_per_actress],
        )
        grouped: dict[int, list[dict]] = {}
        for row in cursor.fetchall():
            data = dict(row)
            data.pop("__rn", None)
            grouped.setdefault(int(data["actress_id"]), []).append(data)
        return grouped


def count_download_candidates(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
) -> int:
    where_clause, params = _candidate_filter_clause(
        status=status,
        actress_id=actress_id,
        source=source,
        q=q,
        needs_magnet=needs_magnet,
        missing_cover=missing_cover,
        latest_event_action=latest_event_action,
    )
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT COUNT(*) AS total
            FROM download_candidates
            {where_clause}
            ''',
            params,
        )
        row = cursor.fetchone()
    return int(row["total"] if row else 0)


def _candidate_filter_clause(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
    table_ref: str = "download_candidates",
) -> tuple[str, list]:
    table_ref = "c" if table_ref == "c" else "download_candidates"
    where = []
    params: list = []
    if status:
        where.append("status = ?")
        params.append(status)
    if actress_id is not None:
        where.append("actress_id = ?")
        params.append(actress_id)
    if source:
        where.append("source = ?")
        params.append(source)
    if q:
        where.append("(content_id LIKE ? OR dvd_id LIKE ? OR title LIKE ? OR actress_name LIKE ?)")
        params.extend([f"%{q}%"] * 4)
    if needs_magnet is True:
        where.append("(magnet IS NULL OR magnet = '')")
    elif needs_magnet is False:
        where.append("(magnet IS NOT NULL AND magnet != '')")
    if missing_cover is True:
        where.append(
            """
            (
                jacket_thumb_url IS NULL
                OR jacket_thumb_url = ''
                OR jacket_thumb_url LIKE '%%noimage%%'
                OR jacket_thumb_url LIKE '%%placeholder%%'
                OR jacket_thumb_url LIKE '%%default%%'
                OR jacket_thumb_url LIKE '%%blank%%'
            )
            """
        )
    elif missing_cover is False:
        where.append(
            """
            (
                jacket_thumb_url IS NOT NULL
                AND jacket_thumb_url != ''
                AND jacket_thumb_url NOT LIKE '%%noimage%%'
                AND jacket_thumb_url NOT LIKE '%%placeholder%%'
                AND jacket_thumb_url NOT LIKE '%%default%%'
                AND jacket_thumb_url NOT LIKE '%%blank%%'
            )
            """
        )
    if latest_event_action == "without_event":
        where.append(
            f"""
            NOT EXISTS (
                SELECT 1
                FROM download_candidate_events latest_event
                WHERE latest_event.candidate_id = {table_ref}.id
            )
            """
        )
    elif latest_event_action:
        where.append(
            f"""
            EXISTS (
                SELECT 1
                FROM download_candidate_events latest_event
                WHERE latest_event.candidate_id = {table_ref}.id
                  AND latest_event.action = ?
                  AND latest_event.id = (
                      SELECT MAX(e.id)
                      FROM download_candidate_events e
                      WHERE e.candidate_id = {table_ref}.id
                  )
            )
            """
        )
        params.append(latest_event_action)
    return (f"WHERE {' AND '.join(where)}" if where else ""), params


def download_candidate_summary(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
) -> dict:
    where_clause, params = _candidate_filter_clause(
        status=status,
        actress_id=actress_id,
        source=source,
        q=q,
        needs_magnet=needs_magnet,
        missing_cover=missing_cover,
        latest_event_action=latest_event_action,
    )
    with get_db() as conn:
        cursor = conn.cursor()
        return _download_candidate_summary_with_cursor(cursor, where_clause, params)


def download_candidate_summary_with_sources(
    status: str | None = None,
    actress_id: int | None = None,
    source: str | None = None,
    q: str | None = None,
    needs_magnet: bool | None = None,
    missing_cover: bool | None = None,
    latest_event_action: str | None = None,
) -> dict:
    where_clause, params = _candidate_filter_clause(
        status=status,
        actress_id=actress_id,
        source=source,
        q=q,
        needs_magnet=needs_magnet,
        missing_cover=missing_cover,
        latest_event_action=latest_event_action,
    )
    with get_db() as conn:
        cursor = conn.cursor()
        summary = _download_candidate_summary_with_cursor(cursor, where_clause, params)
        cursor.execute(
            f'''
            SELECT
                COALESCE(source, 'manual') AS source,
                COUNT(*) AS count,
                SUM(CASE WHEN status = 'candidate' THEN 1 ELSE 0 END) AS candidate_count
            FROM download_candidates
            {where_clause}
            GROUP BY COALESCE(source, 'manual')
            ''',
            params,
        )
        by_source = {}
        candidate_by_source = {}
        for row in cursor.fetchall():
            source_key = row["source"] or "manual"
            count = int(row["count"] or 0)
            candidate_count = int(row["candidate_count"] or 0)
            if count:
                by_source[source_key] = count
            if candidate_count:
                candidate_by_source[source_key] = candidate_count
        latest_event_by_action = _download_candidate_latest_event_counts_with_cursor(
            cursor,
            where_clause,
            params,
        )
        return {
            **summary,
            "by_source": by_source,
            "candidate_by_source": candidate_by_source,
            "latest_event_by_action": latest_event_by_action,
        }


def _download_candidate_summary_with_cursor(cursor, where_clause: str = "", params: list | None = None) -> dict:
    cursor.execute(
        f'''
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'candidate' THEN 1 ELSE 0 END) AS candidate,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE
                WHEN status = 'candidate' AND (magnet IS NULL OR magnet = '') THEN 1
                ELSE 0
            END) AS needs_magnet,
            SUM(CASE
                WHEN status = 'candidate' AND magnet IS NOT NULL AND magnet != '' THEN 1
                ELSE 0
            END) AS ready
        FROM download_candidates
        {where_clause}
        ''',
        params or [],
    )
    row = cursor.fetchone()
    return {key: int(row[key] or 0) for key in _SUMMARY_KEYS}


def _download_candidate_latest_event_counts_with_cursor(
    cursor,
    where_clause: str = "",
    params: list | None = None,
) -> dict[str, int]:
    cursor.execute(
        f'''
        SELECT COALESCE(latest.action, 'without_event') AS action, COUNT(*) AS count
        FROM download_candidates
        LEFT JOIN (
            SELECT event.candidate_id, event.action
            FROM download_candidate_events event
            JOIN (
                SELECT candidate_id, MAX(id) AS max_id
                FROM download_candidate_events
                GROUP BY candidate_id
            ) latest_ids ON latest_ids.max_id = event.id
        ) latest ON latest.candidate_id = download_candidates.id
        {where_clause}
        GROUP BY COALESCE(latest.action, 'without_event')
        ORDER BY count DESC, action
        ''',
        params or [],
    )
    return {
        str(row["action"] or "without_event"): int(row["count"] or 0)
        for row in cursor.fetchall()
        if int(row["count"] or 0) > 0
    }


def get_download_candidate(candidate_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM download_candidates WHERE id = ?", (candidate_id,))
        row = cursor.fetchone()
        rows = [dict(row)] if row else []
    enriched = _enrich_candidate_rows(rows)
    if not enriched:
        return None
    enriched[0]["events"] = list_download_candidate_events(candidate_id)
    return enriched[0]


def update_download_candidate_magnet(
    candidate_id: int,
    magnet: str,
    magnet_source: str = "manual",
) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE download_candidates
            SET magnet = ?, magnet_source = ?, error_msg = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (magnet, magnet_source, candidate_id),
        )
        cursor.execute("SELECT * FROM download_candidates WHERE id = ?", (candidate_id,))
        row = cursor.fetchone()
        if row:
            _bump_download_candidate_generation()
            return dict(row)
        return None


def set_download_candidate_status(
    candidate_id: int,
    status: str,
    download_task_id: int | None = None,
    error_msg: str | None = None,
) -> Optional[dict]:
    if status not in VALID_CANDIDATE_STATUSES:
        raise ValueError(f"invalid download candidate status: {status}")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE download_candidates
            SET status = ?,
                download_task_id = COALESCE(?, download_task_id),
                error_msg = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (status, download_task_id, error_msg, candidate_id),
        )
        cursor.execute("SELECT * FROM download_candidates WHERE id = ?", (candidate_id,))
        row = cursor.fetchone()
        if row:
            _bump_download_candidate_generation()
            return dict(row)
        return None


def bulk_set_download_candidate_status(
    candidate_ids: list[int],
    status: str,
    allowed_current_statuses: set[str] | None = None,
) -> dict:
    if status not in VALID_CANDIDATE_STATUSES:
        raise ValueError(f"invalid download candidate status: {status}")
    ids = [int(candidate_id) for candidate_id in candidate_ids if int(candidate_id) > 0]
    if not ids:
        return {"updated": 0, "skipped": 0, "ids": []}

    with get_db() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        cursor.execute(f"SELECT id, status FROM download_candidates WHERE id IN ({placeholders})", ids)
        rows = [dict(row) for row in cursor.fetchall()]
        allowed_ids = [
            row["id"]
            for row in rows
            if allowed_current_statuses is None or row.get("status") in allowed_current_statuses
        ]
        if allowed_ids:
            update_placeholders = ",".join("?" for _ in allowed_ids)
            cursor.execute(
                f'''
                UPDATE download_candidates
                SET status = ?, error_msg = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({update_placeholders})
                ''',
                [status, *allowed_ids],
            )
        result = {
            "updated": len(allowed_ids),
            "skipped": max(len(ids) - len(allowed_ids), 0),
            "ids": allowed_ids,
        }
        if allowed_ids:
            _bump_download_candidate_generation()
        return result


def download_candidate_stats() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        return _download_candidate_stats_with_cursor(cursor)


def _download_candidate_stats_with_cursor(cursor) -> dict:
    summary = _download_candidate_summary_with_cursor(cursor)
    cursor.execute(
        '''
        SELECT
            COALESCE(source, 'manual') AS source,
            COUNT(*) AS count,
            SUM(CASE WHEN status = 'candidate' THEN 1 ELSE 0 END) AS candidate_count
        FROM download_candidates
        GROUP BY COALESCE(source, 'manual')
        '''
    )
    source_counts = {}
    candidate_source_counts = {}
    for row in cursor.fetchall():
        source = row["source"] or "manual"
        source_counts[source] = int(row["count"] or 0)
        candidate_count = int(row["candidate_count"] or 0)
        if candidate_count:
            candidate_source_counts[source] = candidate_count
    return {
        "candidate": summary["candidate"],
        "approved": summary["approved"],
        "rejected": summary["rejected"],
        "sent": summary["sent"],
        "failed": summary["failed"],
        "by_source": source_counts,
        "candidate_by_source": candidate_source_counts,
        "needs_magnet": summary["needs_magnet"],
        "ready": summary["ready"],
    }


def add_candidate_process_run(
    trigger_source: str,
    policy: str,
    filters: dict | None,
    result: dict | None,
    status: str = "completed",
) -> int:
    result = result or {}
    counts = result.get("counts") or {}
    failed = sum(count for action, count in counts.items() if str(action).startswith("failed"))
    skipped = sum(
        count
        for action, count in counts.items()
        if str(action).startswith("skipped") or action == "manual_required"
    )
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO candidate_process_runs (
                trigger_source, policy, status, filters_json, result_json,
                total, sent, failed, skipped, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (
                trigger_source,
                policy,
                status,
                json.dumps(filters or {}, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                int(result.get("total") or 0),
                int(counts.get("sent") or 0),
                int(failed or 0),
                int(skipped or 0),
            ),
        )
        return cursor.lastrowid


def list_candidate_process_runs(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM candidate_process_runs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            ''',
            (limit,),
        )
        rows = []
        for row in cursor.fetchall():
            data = dict(row)
            for src, dst in (("filters_json", "filters"), ("result_json", "result")):
                raw = data.pop(src, None)
                try:
                    data[dst] = json.loads(raw) if raw else {}
                except Exception:
                    data[dst] = {}
            rows.append(data)
        return rows


def count_auto_sent_candidates_since(hours: int = 24) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT COUNT(*) AS count
            FROM download_candidate_events
            WHERE action = 'auto_approved'
              AND created_at >= (CURRENT_TIMESTAMP + ?::interval)
            ''',
            (f"-{int(hours)} hours",),
        )
        row = cursor.fetchone()
        return int(row["count"] or 0) if row else 0


def get_candidate_process_run(run_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidate_process_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        for src, dst in (("filters_json", "filters"), ("result_json", "result")):
            raw = data.pop(src, None)
            try:
                data[dst] = json.loads(raw) if raw else {}
            except Exception:
                data[dst] = {}
        return data
