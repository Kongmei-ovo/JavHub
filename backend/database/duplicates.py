"""重复记录数据库层"""
from typing import Optional
from database.base import get_db_orig


def add_ignored_duplicate(content_id: Optional[str], emby_item_id: str, reason: Optional[str] = None) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ignored_duplicates (content_id, emby_item_id, reason, ignored_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (content_id, emby_item_id, reason)
    )
    conn.commit()
    dup_id = cursor.lastrowid
    conn.close()
    return dup_id


def is_duplicate_ignored(emby_item_id: str) -> bool:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM ignored_duplicates WHERE emby_item_id = ?", (emby_item_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result
