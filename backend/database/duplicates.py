"""重复记录数据库层"""
from typing import Optional
from database.base import get_db


def add_ignored_duplicate(content_id: Optional[str], emby_item_id: str, reason: Optional[str] = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ignored_duplicates (content_id, emby_item_id, reason, ignored_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (content_id, emby_item_id, reason)
        )
        return cursor.lastrowid


def is_duplicate_ignored(emby_item_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM ignored_duplicates WHERE emby_item_id = ?", (emby_item_id,))
        return cursor.fetchone() is not None
