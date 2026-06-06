"""Global background job model."""
from __future__ import annotations

import json
from contextvars import ContextVar, Token
from datetime import date, datetime
from typing import Any

from psycopg2.extras import Json

from database.base import get_db

_TERMINAL_STATUSES = {"completed", "failed", "canceled"}
_current_job_id_var: ContextVar[int | None] = ContextVar("current_job_id", default=None)


def get_current_job_id() -> int | None:
    """Return the global job id attached to the current async context."""
    return _current_job_id_var.get()


def set_current_job_id(job_id: int | None) -> Token[int | None]:
    return _current_job_id_var.set(int(job_id) if job_id is not None else None)


def ensure_jobs_schema() -> None:
    """Create the global jobs table on first use."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id BIGSERIAL PRIMARY KEY,
                kind TEXT,
                label TEXT,
                status TEXT,
                progress INT DEFAULT 0,
                trace_id TEXT,
                parent_id BIGINT NULL,
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                error_msg TEXT,
                result JSONB,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_created_id
            ON jobs(created_at DESC, id DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_kind_status_created
            ON jobs(kind, status, created_at DESC, id DESC)
            """
        )


def create_job(
    kind: str,
    *,
    label: str | None = None,
    trace_id: str | None = None,
    parent_id: int | None = None,
) -> int:
    ensure_jobs_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (kind, label, status, trace_id, parent_id)
            VALUES (?, ?, 'queued', ?, ?)
            RETURNING id
            """,
            (kind, label, trace_id, parent_id),
        )
        row = cursor.fetchone()
        return int(row["id"])


def update_job(
    job_id: int,
    status: str | None = None,
    *,
    progress: int | None = None,
    label: str | None = None,
    trace_id: str | None = None,
    parent_id: int | None = None,
    error_msg: str | None = None,
    result: Any | None = None,
) -> dict[str, Any] | None:
    ensure_jobs_schema()
    fields: list[str] = []
    params: list[Any] = []

    if status is not None:
        fields.append("status = ?")
        params.append(status)
        if status == "running":
            fields.append("started_at = COALESCE(started_at, now())")
            fields.append("finished_at = NULL")
        elif status in _TERMINAL_STATUSES:
            fields.append("finished_at = COALESCE(finished_at, now())")
    if progress is not None:
        fields.append("progress = ?")
        params.append(_bounded_progress(progress))
    for key, value in (
        ("label", label),
        ("trace_id", trace_id),
        ("parent_id", parent_id),
        ("error_msg", error_msg),
    ):
        if value is not None:
            fields.append(f"{key} = ?")
            params.append(value)
    if result is not None:
        fields.append("result = ?")
        params.append(Json(result))
    if not fields:
        return get_job(job_id)

    params.append(job_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE jobs
            SET {', '.join(fields)}
            WHERE id = ?
            RETURNING id, kind, label, status, progress, trace_id, parent_id,
                      started_at, finished_at, error_msg, result, created_at
            """,
            params,
        )
        return _normalize_job(cursor.fetchone())


def update_job_progress(job_id: int, progress: int) -> dict[str, Any] | None:
    return update_job(job_id, progress=progress)


def get_job(job_id: int) -> dict[str, Any] | None:
    ensure_jobs_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, kind, label, status, progress, trace_id, parent_id,
                   started_at, finished_at, error_msg, result, created_at
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        )
        return _normalize_job(cursor.fetchone())


def list_jobs(
    *,
    kind: str | None = None,
    status: str | None = None,
    since: str | datetime | date | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_jobs_schema()
    where: list[str] = []
    params: list[Any] = []
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if status:
        where.append("status = ?")
        params.append(status)
    if since:
        clause, value = _since_filter(since)
        where.append(clause)
        params.append(value)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(max(1, min(int(limit or 50), 500)))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT id, kind, label, status, progress, trace_id, parent_id,
                   started_at, finished_at, error_msg, result, created_at
            FROM jobs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        )
        return [_normalize_job(row) for row in cursor.fetchall()]


def cancel_job(job_id: int) -> bool:
    ensure_jobs_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE jobs
            SET status = 'canceled',
                finished_at = COALESCE(finished_at, now())
            WHERE id = ?
              AND status NOT IN ('completed', 'failed', 'canceled')
            RETURNING id
            """,
            (job_id,),
        )
        return cursor.fetchone() is not None


def _normalize_job(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    for key in ("id", "parent_id"):
        if data.get(key) is not None:
            data[key] = int(data[key])
    data["progress"] = int(data.get("progress") or 0)
    data["result"] = _json_value(data.get("result"))
    return data


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return value


def _bounded_progress(progress: int) -> int:
    return max(0, min(int(progress), 100))


def _since_filter(since: str | datetime | date) -> tuple[str, Any]:
    if isinstance(since, str):
        value = since.strip()
        if _is_timestamp(value):
            return "created_at >= ?::timestamptz", value
        return "created_at >= (CURRENT_TIMESTAMP - ?::interval)", value
    return "created_at >= ?", since


def _is_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False
