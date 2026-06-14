"""Acquisition session facade: one active acquisition pointer per movie.

This is *not* a second source of truth. Durable facts stay in
``download_candidates`` / ``download_tasks`` / ``movie_resources``; a session
only carries the per-movie activity pointer (→candidate, →download_task), the
UI-facing state machine, the trigger source, and whether the waiting page was
detached. Single-active-per-movie is enforced by a partial unique index
(``idx_acq_session_active_movie``), not an app-layer ``if`` — subscription
concurrency races user clicks.
"""
from __future__ import annotations

from typing import Any

import psycopg2

from database.base import get_db

ACTIVE_STATUSES = ("searching", "options_ready", "submitted", "downloading", "finalizing")
TERMINAL_STATUSES = ("ready", "failed")
ALL_STATUSES = set(ACTIVE_STATUSES) | set(TERMINAL_STATUSES)

# Columns a caller may set through update_acquisition_session. Whitelisted so the
# dynamic SET clause can never interpolate an attacker-controlled column name.
_UPDATABLE_FIELDS = {
    "status",
    "trigger",
    "candidate_id",
    "download_task_id",
    "selected_info_hash",
    "error_code",
    "error_msg",
    "detached",
}


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _validate_status(status: str) -> str:
    value = str(status or "").strip()
    if value not in ALL_STATUSES:
        raise ValueError(f"invalid session status: {status!r}")
    return value


def create_acquisition_session(
    *,
    movie_id: str,
    trigger: str = "user",
    candidate_id: int | None = None,
    download_task_id: int | None = None,
) -> dict[str, Any]:
    """Open a fresh active session. Raises on the partial unique index if the
    movie already has an active session — callers wanting reuse semantics should
    use ``get_or_create_active_session``."""
    mid = str(movie_id or "").strip()
    if not mid:
        raise ValueError("movie_id is required")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO acquisition_sessions (
                movie_id, status, trigger, candidate_id, download_task_id,
                created_at, updated_at
            )
            VALUES (?, 'searching', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (mid, str(trigger or "user").strip() or "user", candidate_id, download_task_id),
        )
        session_id = int(cursor.lastrowid)
    return get_acquisition_session(session_id)


def get_acquisition_session(session_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM acquisition_sessions WHERE id = ?",
            (int(session_id),),
        )
        return _row_to_dict(cursor.fetchone())


def get_active_session_for_movie(movie_id: str) -> dict[str, Any] | None:
    mid = str(movie_id or "").strip()
    if not mid:
        return None
    placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT * FROM acquisition_sessions
            WHERE movie_id = ? AND status IN ({placeholders})
            ORDER BY id DESC
            LIMIT 1
            """,
            (mid, *ACTIVE_STATUSES),
        )
        return _row_to_dict(cursor.fetchone())


def get_or_create_active_session(
    *, movie_id: str, trigger: str = "user"
) -> dict[str, Any]:
    """Reuse the movie's active session if one exists, else open a new one.

    The SELECT-then-INSERT is racy under concurrency (subscription scheduler vs
    user click), so an INSERT that loses the unique-index race is caught and the
    winner's row is returned instead of raising."""
    mid = str(movie_id or "").strip()
    if not mid:
        raise ValueError("movie_id is required")
    existing = get_active_session_for_movie(mid)
    if existing is not None:
        return existing
    try:
        return create_acquisition_session(movie_id=mid, trigger=trigger)
    except psycopg2.IntegrityError:
        winner = get_active_session_for_movie(mid)
        if winner is not None:
            return winner
        raise


def update_acquisition_session(session_id: int, **fields: Any) -> dict[str, Any] | None:
    updates = {key: value for key, value in fields.items() if key in _UPDATABLE_FIELDS}
    if "status" in updates:
        updates["status"] = _validate_status(updates["status"])
    if not updates:
        return get_acquisition_session(session_id)
    set_parts = [f"{column} = ?" for column in updates]
    set_parts.append("updated_at = CURRENT_TIMESTAMP")
    params: list[Any] = list(updates.values())
    params.append(int(session_id))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE acquisition_sessions SET {', '.join(set_parts)} WHERE id = ?",
            tuple(params),
        )
    return get_acquisition_session(session_id)


def finish_acquisition_session(
    session_id: int,
    *,
    status: str,
    error_code: str | None = None,
    error_msg: str | None = None,
) -> dict[str, Any] | None:
    if status not in TERMINAL_STATUSES:
        raise ValueError(f"finish status must be terminal (ready/failed): {status!r}")
    return update_acquisition_session(
        session_id, status=status, error_code=error_code, error_msg=error_msg
    )


def mark_session_detached(session_id: int) -> dict[str, Any] | None:
    """Flag that the user closed the waiting page; the background work continues."""
    return update_acquisition_session(session_id, detached=1)
