"""播放进度数据库层。

单用户先行：user_id 列预留恒为 NULL，多用户化时只改查询不改表。
进度与 Emby 兼容层（Sessions API）共表，Web/Infuse 互通续播。
"""
from __future__ import annotations

from typing import Optional

from database.base import get_db

COMPLETED_RATIO = 0.95
MIN_RESUME_SECONDS = 30


def save_progress(
    content_id: str,
    source: str,
    position_seconds: float,
    duration_seconds: float = 0,
) -> dict:
    """Upsert 进度。position/duration >= 95% 时置 completed=1。"""
    position_seconds = max(float(position_seconds or 0), 0.0)
    duration_seconds = max(float(duration_seconds or 0), 0.0)
    completed = 1 if duration_seconds > 0 and position_seconds / duration_seconds >= COMPLETED_RATIO else 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM playback_progress WHERE content_id = ? AND source = ? AND user_id IS NULL",
            (content_id, source),
        )
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                """
                INSERT INTO playback_progress (
                    content_id, user_id, source, position_seconds, duration_seconds,
                    completed, updated_at
                )
                VALUES (?, NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (content_id, source, position_seconds, duration_seconds, completed),
            )
        else:
            cursor.execute(
                """
                UPDATE playback_progress
                SET position_seconds = ?, duration_seconds = ?, completed = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (position_seconds, duration_seconds, completed, dict(row)["id"]),
            )
    return {
        "content_id": content_id,
        "source": source,
        "position_seconds": position_seconds,
        "duration_seconds": duration_seconds,
        "completed": completed,
    }


def get_progress(content_id: str, source: str | None = None) -> Optional[dict]:
    """取进度。不指定 source 时返回最近更新的一条。"""
    with get_db() as conn:
        cursor = conn.cursor()
        if source:
            cursor.execute(
                "SELECT * FROM playback_progress WHERE content_id = ? AND source = ? AND user_id IS NULL",
                (content_id, source),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM playback_progress
                WHERE content_id = ? AND user_id IS NULL
                ORDER BY updated_at DESC LIMIT 1
                """,
                (content_id,),
            )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_progress_map(content_ids: list[str], source: str | None = None) -> dict[str, dict]:
    """Batch-load the newest progress row for each requested content ID."""
    ids = list(dict.fromkeys(str(content_id) for content_id in content_ids if content_id))
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    params: list[object] = list(ids)
    source_clause = ""
    if source:
        source_clause = " AND source = ?"
        params.append(source)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT * FROM playback_progress
            WHERE user_id IS NULL
              AND content_id IN ({placeholders})
              {source_clause}
            ORDER BY updated_at DESC
            """,
            params,
        )
        result: dict[str, dict] = {}
        for row in cursor.fetchall():
            item = dict(row)
            result.setdefault(str(item["content_id"]), item)
        return result


def list_playback_progress(source: str | None = None) -> list[dict]:
    """Return the single-user playback index in most-recently-played order."""
    with get_db() as conn:
        cursor = conn.cursor()
        if source:
            cursor.execute(
                """
                SELECT * FROM playback_progress
                WHERE user_id IS NULL AND source = ?
                ORDER BY updated_at DESC
                """,
                (source,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM playback_progress
                WHERE user_id IS NULL
                ORDER BY updated_at DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def list_continue_watching(limit: int = 12) -> list[dict]:
    """继续观看：未看完、位置超过 MIN_RESUME_SECONDS，按最近播放排序，番号去重。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM playback_progress
            WHERE user_id IS NULL AND completed = 0 AND position_seconds >= ?
            ORDER BY updated_at DESC
            """,
            (MIN_RESUME_SECONDS,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
    seen: set[str] = set()
    result: list[dict] = []
    for row in rows:
        if row["content_id"] in seen:
            continue
        seen.add(row["content_id"])
        result.append(row)
        if len(result) >= limit:
            break
    return result


def delete_progress(content_id: str, source: str | None = None) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        if source:
            cursor.execute(
                "DELETE FROM playback_progress WHERE content_id = ? AND source = ? AND user_id IS NULL",
                (content_id, source),
            )
        else:
            cursor.execute(
                "DELETE FROM playback_progress WHERE content_id = ? AND user_id IS NULL",
                (content_id,),
            )
        return cursor.rowcount > 0
