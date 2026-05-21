from fastapi import APIRouter, Query
from database import add_log, get_db_orig

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

@router.get("")
async def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
):
    """
    获取日志列表
    limit: 返回数量，默认100
    level: 过滤级别 (INFO/WARNING/ERROR)
    """
    conn = get_db_orig()
    cursor = conn.cursor()

    where = []
    params = []
    if level:
        where.append("level = ?")
        params.append(level.upper())
    if q:
        where.append("message LIKE ?")
        params.append(f"%{q}%")
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    cursor.execute(f"SELECT COUNT(*) AS total FROM logs{where_sql}", params)
    total = int(cursor.fetchone()["total"])
    cursor.execute(
        f"SELECT * FROM logs{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )

    rows = cursor.fetchall()
    conn.close()

    return {"data": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

@router.post("")
async def add_log_entry(level: str, message: str):
    """写入日志"""
    add_log(level.upper(), message)
    return {"success": True}

@router.delete("")
async def clear_logs():
    """清空日志"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM logs')
    conn.commit()
    conn.close()
    return {"success": True}
