"""下载任务数据库层"""
from typing import Optional
from database.base import get_db_orig


def create_download_task(content_id: str, title: str, magnet: str, path: Optional[str] = None) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO download_tasks (content_id, title, magnet, path, status, created_at) VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
        (content_id, title, magnet, path)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_download_tasks(limit: int = 100) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_task_status(task_id: int, status: str, error_msg: Optional[str] = None):
    conn = get_db_orig()
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
    conn.commit()
    conn.close()


def delete_download_task(task_id: int):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM download_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
