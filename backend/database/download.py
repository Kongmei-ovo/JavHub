"""下载任务数据库层"""
from typing import Optional
from database.base import get_db


def create_download_task(content_id: str, title: str, magnet: str, path: Optional[str] = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO download_tasks (content_id, title, magnet, path, status, created_at) VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
            (content_id, title, magnet, path)
        )
        return cursor.lastrowid


def get_download_tasks(limit: int = 100) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_task_status(task_id: int, status: str, error_msg: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if error_msg:
            cursor.execute(
                "UPDATE download_tasks SET status = ?, error_msg = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_msg, task_id)
            )
        else:
            cursor.execute(
                "UPDATE download_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, task_id)
            )


def delete_download_task(task_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM download_tasks WHERE id = ?", (task_id,))
