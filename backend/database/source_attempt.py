"""Source attempt persistence and health summaries."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from database.base import get_db

RETENTION_LIMIT = 2000


def ensure_source_attempt_schema() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS source_attempts (
                id BIGSERIAL PRIMARY KEY,
                source TEXT,
                keyword TEXT,
                ok BOOLEAN,
                duration_ms NUMERIC,
                result_count INT,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_attempts_source_created_at
            ON source_attempts(source, created_at DESC)
            """
        )


def record_source_attempt(
    *,
    source: str,
    keyword: str,
    ok: bool,
    duration_ms: float,
    result_count: int,
    error: str = "",
    created_at: datetime | None = None,
    retention_limit: int = RETENTION_LIMIT,
    prune_chance: float = 0.05,
) -> None:
    ensure_source_attempt_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        if created_at is None:
            cursor.execute(
                """
                INSERT INTO source_attempts (source, keyword, ok, duration_ms, result_count, error)
                VALUES (?, ?, ?::boolean, ?, ?, ?)
                """,
                (source, keyword, ok, duration_ms, result_count, error),
            )
        else:
            cursor.execute(
                """
                INSERT INTO source_attempts (source, keyword, ok, duration_ms, result_count, error, created_at)
                VALUES (?, ?, ?::boolean, ?, ?, ?, ?)
                """,
                (source, keyword, ok, duration_ms, result_count, error, created_at),
            )
        if _should_prune(prune_chance):
            _prune_source_attempts(cursor, retention_limit)


def list_recent_source_attempts(limit: int = 100) -> list[dict[str, Any]]:
    ensure_source_attempt_schema()
    bounded_limit = max(0, min(int(limit or 0), RETENTION_LIMIT))
    if bounded_limit <= 0:
        return []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, source, keyword, ok, duration_ms, result_count, error, created_at
            FROM source_attempts
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (bounded_limit,),
        )
        return [_normalize_attempt(row) for row in cursor.fetchall()]


def source_health_summary(window_minutes: int = 60) -> list[dict[str, Any]]:
    ensure_source_attempt_schema()
    bounded_minutes = max(1, int(window_minutes or 60))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH recent AS (
                SELECT source, ok, duration_ms, error, created_at
                FROM source_attempts
                WHERE created_at >= (now() - (?::int * INTERVAL '1 minute'))
            ),
            last_errors AS (
                SELECT DISTINCT ON (source) source, COALESCE(error, '') AS error
                FROM recent
                WHERE NOT ok AND COALESCE(error, '') <> ''
                ORDER BY source, created_at DESC
            )
            SELECT
                recent.source AS name,
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE recent.ok)::int AS ok,
                COALESCE(
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY recent.duration_ms),
                    0
                ) AS p50_ms,
                COALESCE(
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY recent.duration_ms),
                    0
                ) AS p95_ms,
                COALESCE(last_errors.error, '') AS last_error
            FROM recent
            LEFT JOIN last_errors ON last_errors.source = recent.source
            GROUP BY recent.source, last_errors.error
            ORDER BY recent.source
            """,
            (bounded_minutes,),
        )
        return [_normalize_health(row) for row in cursor.fetchall()]


def _should_prune(chance: float) -> bool:
    if chance <= 0:
        return False
    if chance >= 1:
        return True
    return random.random() < chance


def _prune_source_attempts(cursor, retention_limit: int) -> None:
    bounded_limit = max(1, int(retention_limit or RETENTION_LIMIT))
    cursor.execute(
        """
        DELETE FROM source_attempts
        WHERE id IN (
            SELECT id
            FROM source_attempts
            ORDER BY created_at DESC, id DESC
            OFFSET ?
        )
        """,
        (bounded_limit,),
    )


def _normalize_attempt(row: Any) -> dict[str, Any]:
    data = dict(row or {})
    return {
        "id": int(data.get("id") or 0),
        "source": str(data.get("source") or ""),
        "keyword": str(data.get("keyword") or ""),
        "ok": bool(data.get("ok")),
        "duration_ms": float(data.get("duration_ms") or 0),
        "result_count": int(data.get("result_count") or 0),
        "error": str(data.get("error") or ""),
        "created_at": str(data.get("created_at") or ""),
    }


def _normalize_health(row: Any) -> dict[str, Any]:
    data = dict(row or {})
    total = int(data.get("total") or 0)
    ok_count = int(data.get("ok") or 0)
    return {
        "name": str(data.get("name") or ""),
        "total": total,
        "ok": ok_count,
        "ok_ratio": (ok_count / total) if total else 0,
        "p50_ms": float(data.get("p50_ms") or 0),
        "p95_ms": float(data.get("p95_ms") or 0),
        "last_error": str(data.get("last_error") or ""),
    }
