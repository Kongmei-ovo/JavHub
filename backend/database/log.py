"""日志数据库层"""
from typing import Optional
from database.base import get_db_orig


def add_log(level: str, message: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (level, message))
    conn.commit()
    conn.close()


def get_logs(limit: int = 100, level: Optional[str] = None) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    if level:
        cursor.execute("SELECT * FROM logs WHERE level = ? ORDER BY created_at DESC LIMIT ?", (level, limit))
    else:
        cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
