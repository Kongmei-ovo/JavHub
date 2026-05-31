"""日志数据库层"""
import time
from typing import Any, Optional
from database.base import get_db


def _bump_logs_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("logs", time.time_ns())
    except Exception:
        pass


def add_log(level: str, message: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (level, message))
    _bump_logs_generation()


def _log_filters(level: Optional[str] = None, q: Optional[str] = None) -> tuple[str, list[Any]]:
    where = []
    params = []
    if level:
        where.append("level = ?")
        params.append(level)
    if q:
        where.append("message LIKE ?")
        params.append(f"%{q}%")
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    return where_sql, params


def list_logs(
    limit: int = 100,
    level: Optional[str] = None,
    q: Optional[str] = None,
    offset: int = 0,
) -> tuple[list[dict], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        where_sql, params = _log_filters(level=level, q=q)

        cursor.execute(f"SELECT COUNT(*) AS total FROM logs{where_sql}", params)
        total = int(cursor.fetchone()["total"])
        cursor.execute(
            f"SELECT * FROM logs{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows], total


def get_logs(limit: int = 100, level: Optional[str] = None) -> list:
    rows, _total = list_logs(limit=limit, level=level)
    return rows


def clear_logs():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logs")
    _bump_logs_generation()
