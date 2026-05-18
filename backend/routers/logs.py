from fastapi import APIRouter
from database import add_log, get_db_orig

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

@router.get("")
async def get_logs(limit: int = 100, level: str = None):
    """
    获取日志列表
    limit: 返回数量，默认100
    level: 过滤级别 (INFO/WARNING/ERROR)
    """
    conn = get_db_orig()
    cursor = conn.cursor()

    if level:
        cursor.execute(
            'SELECT * FROM logs WHERE level = ? ORDER BY created_at DESC LIMIT ?',
            (level.upper(), limit)
        )
    else:
        cursor.execute(
            'SELECT * FROM logs ORDER BY created_at DESC LIMIT ?',
            (limit,)
        )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

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
