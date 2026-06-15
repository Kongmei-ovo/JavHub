"""Exempt-video data layer.

A small survivor of the retired inventory/missing machinery: ``is_video_exempt``
still gates subscription/candidate auto-acquire so flagged codes are never
re-queued. Add/get/delete remain for API-level management of the exemption set.
"""
from database.base import get_db


def add_exempt_video(content_id: str, actress_id: int, reason: str, created_by: str = "manual") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO exempt_videos (content_id, actress_id, reason, created_by, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_id) DO UPDATE SET
                reason = excluded.reason,
                actress_id = excluded.actress_id
        ''', (content_id, actress_id, reason, created_by))
        return cursor.lastrowid or 0


def get_exempt_videos() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exempt_videos ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_exempt_video(content_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exempt_videos WHERE content_id = ?", (content_id,))


def is_video_exempt(content_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM exempt_videos WHERE content_id = ?", (content_id,))
        return cursor.fetchone() is not None
