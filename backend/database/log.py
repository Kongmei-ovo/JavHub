"""日志数据库层"""
from typing import Optional
from database.base import get_db


def add_log(level: str, message: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (level, message))


def get_logs(limit: int = 100, level: Optional[str] = None) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        if level:
            cursor.execute("SELECT * FROM logs WHERE level = ? ORDER BY created_at DESC LIMIT ?", (level, limit))
        else:
            cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
