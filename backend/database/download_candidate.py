"""Download candidate database layer."""
from __future__ import annotations

import json
from typing import Optional

from database.base import get_db


VALID_CANDIDATE_STATUSES = {"candidate", "approved", "rejected", "sent", "failed"}


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
            ON CONFLICT(content_id, source) DO UPDATE SET
                dvd_id = COALESCE(excluded.dvd_id, download_candidates.dvd_id),
                title = COALESCE(excluded.title, download_candidates.title),
                actress_id = COALESCE(excluded.actress_id, download_candidates.actress_id),
                actress_name = COALESCE(excluded.actress_name, download_candidates.actress_name),
                jacket_thumb_url = COALESCE(excluded.jacket_thumb_url, download_candidates.jacket_thumb_url),
                release_date = COALESCE(excluded.release_date, download_candidates.release_date),
                reason = COALESCE(excluded.reason, download_candidates.reason),
                status = CASE
                    WHEN download_candidates.status IN ('rejected', 'sent', 'failed') THEN download_candidates.status
                    ELSE excluded.status
                END,
                magnet = COALESCE(download_candidates.magnet, excluded.magnet),
                magnet_source = COALESCE(download_candidates.magnet_source, excluded.magnet_source),
                updated_at = CURRENT_TIMESTAMP
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
        cursor.execute(
            "SELECT * FROM download_candidates WHERE content_id = ? AND source = ?",
            (content_id, source),
        )
        return dict(cursor.fetchone())


def upsert_candidate_from_video(
    video: dict,
    actress_id: int | None,
    actress_name: str | None,
    source: str,
    reason: str,
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
    )


def _enrich_candidate_rows(rows: list[dict]) -> list[dict]:
    task_ids = [row.get("download_task_id") for row in rows if row.get("download_task_id")]
    with get_db() as conn:
        cursor = conn.cursor()
        tasks = {}
        if task_ids:
            placeholders = ",".join("?" for _ in task_ids)
            cursor.execute(
                f"SELECT id, status, error_msg, path, created_at, updated_at FROM download_tasks WHERE id IN ({placeholders})",
                task_ids,
            )
            tasks = {row["id"]: dict(row) for row in cursor.fetchall()}
        candidate_ids = [row.get("id") for row in rows if row.get("id")]
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
        return cursor.lastrowid


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
    limit: int = 200,
) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
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
        where_clause = f"WHERE {' AND '.join(where)}" if where else ""
        cursor.execute(
            f'''
            SELECT * FROM download_candidates
            {where_clause}
            ORDER BY
                CASE status
                    WHEN 'candidate' THEN 0
                    WHEN 'approved' THEN 1
                    WHEN 'failed' THEN 2
                    WHEN 'sent' THEN 3
                    ELSE 4
                END,
                release_date DESC,
                created_at DESC
            LIMIT ?
            ''',
            params + [limit],
        )
        rows = [dict(row) for row in cursor.fetchall()]
    return _enrich_candidate_rows(rows)


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
        return dict(row) if row else None


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
        return dict(row) if row else None


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
        return {
            "updated": len(allowed_ids),
            "skipped": max(len(ids) - len(allowed_ids), 0),
            "ids": allowed_ids,
        }


def download_candidate_stats() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) AS count FROM download_candidates GROUP BY status")
        counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        cursor.execute("SELECT source, COUNT(*) AS count FROM download_candidates GROUP BY source")
        source_counts = {row["source"] or "manual": row["count"] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT source, COUNT(*) AS count FROM download_candidates WHERE status = 'candidate' GROUP BY source"
        )
        candidate_source_counts = {row["source"] or "manual": row["count"] for row in cursor.fetchall()}
    return {
        "candidate": counts.get("candidate", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "sent": counts.get("sent", 0),
        "failed": counts.get("failed", 0),
        "by_source": source_counts,
        "candidate_by_source": candidate_source_counts,
        "needs_magnet": sum(
            1 for row in list_download_candidates(status="candidate", limit=100000)
            if not row.get("magnet")
        ),
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
              AND created_at >= datetime('now', ?)
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
