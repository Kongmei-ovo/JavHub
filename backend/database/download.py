"""下载任务数据库层"""
import time
from typing import Optional
from database.base import get_db


def _bump_download_task_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("download_tasks", time.time_ns())
    except Exception:
        pass


def create_download_task(
    content_id: str,
    title: str,
    magnet: str,
    path: Optional[str] = None,
    downloader_id: Optional[str] = None,
    downloader_name: Optional[str] = None,
    downloader_type: Optional[str] = None,
    movie_id: Optional[str] = None,
    info_hash: Optional[str] = None,
    target_folder_id: Optional[str] = None,
    open115_task_id: Optional[str] = None,
    result_file_id: Optional[str] = None,
    kind: str = "movie",
) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO download_tasks (
                content_id, movie_id, title, magnet, path,
                downloader_id, downloader_name, downloader_type,
                info_hash, target_folder_id, open115_task_id, result_file_id,
                kind, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """,
            (
                content_id,
                movie_id or content_id,
                title,
                magnet,
                path,
                downloader_id,
                downloader_name,
                downloader_type,
                info_hash,
                target_folder_id,
                open115_task_id,
                result_file_id,
                kind,
            )
        )
        task_id = cursor.lastrowid
        _bump_download_task_generation()
        return task_id


def get_download_tasks(limit: int = 100) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_download_task(task_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM download_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_task_status(
    task_id: int,
    status: str,
    error_msg: Optional[str] = None,
    remote_task_id: Optional[str] = None,
    *,
    info_hash: Optional[str] = None,
    target_folder_id: Optional[str] = None,
    open115_task_id: Optional[str] = None,
    result_file_id: Optional[str] = None,
    path: Optional[str] = None,
):
    with get_db() as conn:
        cursor = conn.cursor()
        fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        if error_msg is not None:
            fields.append("error_msg = ?")
            params.append(error_msg)
        if remote_task_id is not None:
            fields.append("remote_task_id = ?")
            params.append(remote_task_id)
        for field, value in (
            ("info_hash", info_hash),
            ("target_folder_id", target_folder_id),
            ("open115_task_id", open115_task_id),
            ("result_file_id", result_file_id),
            ("path", path),
        ):
            if value is not None:
                fields.append(f"{field} = ?")
                params.append(value)
        params.append(task_id)
        cursor.execute(
            f"UPDATE download_tasks SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        if cursor.rowcount > 0:
            _bump_download_task_generation()


def delete_download_task(task_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM download_tasks WHERE id = ?", (task_id,))
        if cursor.rowcount > 0:
            _bump_download_task_generation()
