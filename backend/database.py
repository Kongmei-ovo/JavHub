import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "avdownloader.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_tasks (
            id TEXT PRIMARY KEY,
            content_id TEXT,
            title TEXT,
            magnet TEXT,
            path TEXT,
            status TEXT DEFAULT 'pending',
            error_msg TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actress_id INTEGER,
            actress_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            auto_download INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ignored_duplicates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT,
            emby_item_id TEXT NOT NULL,
            ignored_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actress_missing_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actress_id INTEGER NOT NULL UNIQUE,
            actress_name TEXT NOT NULL,
            total_in_javinfo INTEGER,
            missing_count INTEGER,
            missing_videos_json TEXT,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# === Download Tasks ===

def create_download_task(content_id: str, title: str, magnet: str, path: Optional[str] = None) -> int:
    """创建下载任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO download_tasks (content_id, title, magnet, path, status, created_at) VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
        (content_id, title, magnet, path)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def get_download_tasks(limit: int = 100) -> List[dict]:
    """获取下载任务列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_task_status(task_id: int, status: str, error_msg: Optional[str] = None):
    """更新下载任务状态"""
    conn = get_db()
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
    """删除下载任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM download_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# === Subscriptions ===

def add_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> int:
    """添加订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subscriptions (actress_id, actress_name, auto_download, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, auto_download)
    )
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id

def get_subscriptions() -> List[dict]:
    """获取订阅列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_subscription(subscription_id: int):
    """删除订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
    conn.commit()
    conn.close()

# === Logs ===

def add_log(level: str, message: str):
    """添加日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (level, message))
    conn.commit()
    conn.close()

def get_logs(limit: int = 100, level: Optional[str] = None) -> List[dict]:
    """获取日志"""
    conn = get_db()
    cursor = conn.cursor()
    if level:
        cursor.execute("SELECT * FROM logs WHERE level = ? ORDER BY created_at DESC LIMIT ?", (level, limit))
    else:
        cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# === Duplicates ===

def add_ignored_duplicate(content_id: Optional[str], emby_item_id: str, reason: Optional[str] = None) -> int:
    """添加忽略的重复记录"""
    conn = get_db()
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
    """检查是否已被用户忽略"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM ignored_duplicates WHERE emby_item_id = ?", (emby_item_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# === Missing Summary ===

def save_missing_summary(actress_id: int, actress_name: str, total: int, missing: int, videos_json: str):
    """保存或更新缺失统计缓存"""
    conn = get_db()
    cursor = conn.cursor()
    # 先删除旧的
    cursor.execute("DELETE FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    # 再插入新的
    cursor.execute(
        "INSERT INTO actress_missing_summary (actress_id, actress_name, total_in_javinfo, missing_count, missing_videos_json, last_updated) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, total, missing, videos_json)
    )
    conn.commit()
    conn.close()

def get_all_missing_summaries() -> List[dict]:
    """获取所有缺失统计缓存"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary ORDER BY missing_count DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_missing_summary(actress_id: int) -> Optional[dict]:
    """获取指定演员的缺失统计"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
