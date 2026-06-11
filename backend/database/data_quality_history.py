"""Data quality history snapshots."""
from __future__ import annotations

from typing import Any

from psycopg2.extras import Json

from database.base import get_db

_CAPTURED_DAY_EXPR = "((captured_at AT TIME ZONE 'Asia/Shanghai')::date)"
_TODAY_EXPR = "((CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Shanghai')::date)"


def ensure_data_quality_history_schema() -> None:
    """Create the daily data quality snapshot table on first use."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS data_quality_snapshots (
                id BIGSERIAL PRIMARY KEY,
                captured_at TIMESTAMPTZ DEFAULT now(),
                summary JSONB NOT NULL DEFAULT '{}'::jsonb,
                issues_by_type JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )
        cursor.execute(
            """
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = 'idx_data_quality_snapshots_captured_day'
            """
        )
        existing = cursor.fetchone()
        existing_def = ""
        if existing:
            existing_def = str(existing.get("indexdef") if isinstance(existing, dict) else existing[0] or "")
        if existing and "Asia/Shanghai" not in existing_def:
            cursor.execute("DROP INDEX IF EXISTS idx_data_quality_snapshots_captured_day")
        cursor.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_data_quality_snapshots_captured_day
            ON data_quality_snapshots ({_CAPTURED_DAY_EXPR})
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_data_quality_snapshots_captured_at
            ON data_quality_snapshots(captured_at DESC)
            """
        )


def upsert_today_snapshot(summary: dict[str, Any], issues_by_type: dict[str, Any]) -> dict[str, Any]:
    """Insert or replace today's snapshot, returning the stored row."""
    ensure_data_quality_history_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO data_quality_snapshots (summary, issues_by_type)
            VALUES (?, ?)
            ON CONFLICT ({_CAPTURED_DAY_EXPR})
            DO UPDATE SET
                captured_at = now(),
                summary = EXCLUDED.summary,
                issues_by_type = EXCLUDED.issues_by_type
            RETURNING id, captured_at, summary, issues_by_type
            """,
            (Json(summary or {}), Json(issues_by_type or {})),
        )
        return _normalize_snapshot(cursor.fetchone())


def list_data_quality_history(days: int = 14) -> list[dict[str, Any]]:
    """Return daily snapshots from the requested trailing day window."""
    bounded_days = max(1, min(int(days or 14), 90))
    ensure_data_quality_history_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                id,
                captured_at,
                {_CAPTURED_DAY_EXPR} AS captured_date,
                summary,
                issues_by_type
            FROM data_quality_snapshots
            WHERE {_CAPTURED_DAY_EXPR} >= ({_TODAY_EXPR} - (?::int - 1))
            ORDER BY {_CAPTURED_DAY_EXPR} ASC, captured_at ASC, id ASC
            """,
            (bounded_days,),
        )
        return [_normalize_snapshot(row) for row in cursor.fetchall()]


def _normalize_snapshot(row: Any) -> dict[str, Any]:
    data = dict(row or {})
    captured_at = str(data.get("captured_at") or "")
    captured_date = str(data.get("captured_date") or "")
    if not captured_date and captured_at:
        captured_date = captured_at[:10]
    return {
        "id": int(data.get("id") or 0),
        "captured_at": captured_at,
        "date": captured_date,
        "summary": _dict_value(data.get("summary")),
        "issues_by_type": _dict_value(data.get("issues_by_type")),
    }


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
