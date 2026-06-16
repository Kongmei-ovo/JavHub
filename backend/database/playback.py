"""播放进度数据库层。

单用户先行：user_id 列预留恒为 NULL，多用户化时只改查询不改表。
进度与 Emby 兼容层（Sessions API）共表，Web/Infuse 互通续播。
"""
from __future__ import annotations

from typing import Optional

from database.base import get_db

COMPLETED_RATIO = 0.95
MIN_RESUME_SECONDS = 30
LEGACY_PROGRESS_SOURCE = "library"


def save_progress(
    content_id: str,
    source: str,
    position_seconds: float,
    duration_seconds: float = 0,
    resource_id: int | None = None,
) -> dict:
    """Upsert 进度。position/duration >= 95% 时置 completed=1。"""
    position_seconds = max(float(position_seconds or 0), 0.0)
    duration_seconds = max(float(duration_seconds or 0), 0.0)
    resource_id = int(resource_id) if resource_id is not None else None
    completed = 1 if duration_seconds > 0 and position_seconds / duration_seconds >= COMPLETED_RATIO else 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO playback_progress (
                content_id, user_id, source, last_source, last_resource_id,
                position_seconds, duration_seconds, completed, updated_at
            )
            VALUES (?, NULL, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (content_id) DO UPDATE SET
                source = EXCLUDED.source,
                last_source = EXCLUDED.last_source,
                last_resource_id = EXCLUDED.last_resource_id,
                position_seconds = EXCLUDED.position_seconds,
                duration_seconds = EXCLUDED.duration_seconds,
                completed = EXCLUDED.completed,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                content_id,
                LEGACY_PROGRESS_SOURCE,
                source,
                resource_id,
                position_seconds,
                duration_seconds,
                completed,
            ),
        )
    return {
        "content_id": content_id,
        "source": source,
        "last_source": source,
        "last_resource_id": resource_id,
        "position_seconds": position_seconds,
        "duration_seconds": duration_seconds,
        "completed": completed,
    }


def get_progress(content_id: str, source: str | None = None) -> Optional[dict]:
    """取影片级进度；source 仅作为旧调用兼容参数。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM playback_progress
            WHERE content_id = ? AND user_id IS NULL
            LIMIT 1
            """,
            (content_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_progress_map(content_ids: list[str], source: str | None = None) -> dict[str, dict]:
    """Batch-load movie-level progress for the requested content IDs only."""
    ids = list(dict.fromkeys(str(content_id) for content_id in content_ids if content_id))
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT * FROM playback_progress
            WHERE user_id IS NULL
              AND content_id IN ({placeholders})
            """,
            ids,
        )
        return {
            str(item["content_id"]): item
            for item in (dict(row) for row in cursor.fetchall())
        }


def list_playback_progress(source: str | None = None) -> list[dict]:
    """Return movie-level progress; source is retained for old callers."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM playback_progress
            WHERE user_id IS NULL
            ORDER BY updated_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def list_continue_watching(limit: int = 12) -> list[dict]:
    """继续观看：未看完、位置超过 MIN_RESUME_SECONDS，按最近播放排序。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM playback_progress
            WHERE user_id IS NULL AND completed = 0 AND position_seconds >= ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (MIN_RESUME_SECONDS, max(int(limit), 0)),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_progress(content_id: str, source: str | None = None) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM playback_progress WHERE content_id = ? AND user_id IS NULL",
            (content_id,),
        )
        return cursor.rowcount > 0
