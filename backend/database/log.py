"""日志数据库层"""
import random
import time
from typing import Any, Optional
from database.base import get_db
from middlewares.trace import get_trace_id

# 运行日志是滚动汇总：只保留最近 N 条，超出的最旧记录在写入时按小概率自动清理，
# 避免标准 logging 桥接进来后无限增长（仿 source_attempt 的 prune 模式）。
LOG_RETENTION_LIMIT = 20000


def _bump_logs_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("logs", time.time_ns())
    except Exception:
        pass


def _ensure_trace_id_column(cursor) -> None:
    cursor.execute("ALTER TABLE logs ADD COLUMN trace_id TEXT")


def add_log(level: str, message: str, trace_id: str | None = None):
    current_trace_id = trace_id if trace_id is not None else get_trace_id()
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_trace_id_column(cursor)
        cursor.execute(
            "INSERT INTO logs (level, message, trace_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (level, message, current_trace_id),
        )
        if _should_prune(0.05):
            _prune_logs(cursor, LOG_RETENTION_LIMIT)
    _bump_logs_generation()


def _should_prune(chance: float) -> bool:
    if chance <= 0:
        return False
    if chance >= 1:
        return True
    return random.random() < chance


def _prune_logs(cursor, retention_limit: int = LOG_RETENTION_LIMIT) -> None:
    """删除超出保留上限的最旧日志，只留最近 retention_limit 条。"""
    bounded_limit = max(1, int(retention_limit or LOG_RETENTION_LIMIT))
    cursor.execute(
        """
        DELETE FROM logs
        WHERE id IN (
            SELECT id
            FROM logs
            ORDER BY created_at DESC, id DESC
            OFFSET ?
        )
        """,
        (bounded_limit,),
    )


def _log_filters(
    level: Optional[str] = None,
    q: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> tuple[str, list[Any]]:
    where = []
    params = []
    if level:
        where.append("level = ?")
        params.append(level)
    if q:
        where.append("message LIKE ?")
        params.append(f"%{q}%")
    if trace_id:
        where.append("trace_id = ?")
        params.append(trace_id)
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    return where_sql, params


def list_logs(
    limit: int = 100,
    level: Optional[str] = None,
    q: Optional[str] = None,
    trace_id: Optional[str] = None,
    offset: int = 0,
) -> tuple[list[dict], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        _ensure_trace_id_column(cursor)
        where_sql, params = _log_filters(level=level, q=q, trace_id=trace_id)

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


def count_by_level(since_minutes: Optional[int] = None) -> dict[str, int]:
    """按等级统计日志条数；since_minutes 给定时只统计最近这么多分钟内的。

    cutoff 用 Postgres NOW() 在库内计算（created_at 是 TIMESTAMPTZ），
    避免 Python 端 naive/aware 时区错配。None 或 <=0 表示全量。
    """
    counts = {"error": 0, "warning": 0, "info": 0}
    with get_db() as conn:
        cursor = conn.cursor()
        if since_minutes is not None and since_minutes > 0:
            cursor.execute(
                "SELECT level, COUNT(*) AS n FROM logs "
                "WHERE created_at >= NOW() - (? || ' minutes')::interval "
                "GROUP BY level",
                (int(since_minutes),),
            )
        else:
            cursor.execute("SELECT level, COUNT(*) AS n FROM logs GROUP BY level")
        for row in cursor.fetchall():
            level_key = str(row["level"] or "").lower()
            if level_key in counts:
                counts[level_key] = int(row["n"])
    return counts


def clear_logs():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logs")
    _bump_logs_generation()
