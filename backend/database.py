"""翻译映射数据库层"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "avdownloader.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==============================================
# 翻译映射表
# 两类存储：
# 1. per-content_id 翻译：存储 { type: { "field": "value" } }，key = content_id
# 2. global name 翻译：存储 { type: "translated_name" }，key = "_global:{type}:{original_name}"
# ==============================================

def init_translation_db():
    """初始化翻译映射表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translation_mappings (
            content_id TEXT PRIMARY KEY,
            actress_json TEXT DEFAULT '{}',
            category_json TEXT DEFAULT '{}',
            series_json TEXT DEFAULT '{}',
            title_json TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def _get_raw(content_id: str) -> Optional[dict]:
    """获取原始记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT actress_json, category_json, series_json, title_json, maker_json, label_json FROM translation_mappings WHERE content_id = ?",
        (content_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "actress": json.loads(row["actress_json"] or "{}"),
        "category": json.loads(row["category_json"] or "{}"),
        "series": json.loads(row["series_json"] or "{}"),
        "title": json.loads(row["title_json"] or "{}"),
        "maker": json.loads(row["maker_json"] or "{}"),
        "label": json.loads(row["label_json"] or "{}"),
    }

def get_translation(content_id: str) -> Optional[dict]:
    """获取翻译映射（per-content_id 或 global）"""
    # 先查精确 content_id
    result = _get_raw(content_id)
    if result:
        return result
    # 查 global actress 映射
    result = _get_raw("_global:actress:" + content_id)
    if result:
        return result
    # 查 global category 映射
    result = _get_raw("_global:category:" + content_id)
    if result:
        return result
    # 查 global series 映射
    result = _get_raw("_global:series:" + content_id)
    if result:
        return result
    return None

def upsert_translation(content_id: str, mapping: dict) -> bool:
    """插入或更新翻译映射（部分更新）"""
    existing = _get_raw(content_id)
    conn = get_db()
    cursor = conn.cursor()
    if existing:
        merged = {
            "actress": {**existing.get("actress", {}), **mapping.get("actress", {})},
            "category": {**existing.get("category", {}), **mapping.get("category", {})},
            "series": {**existing.get("series", {}), **mapping.get("series", {})},
            "title": mapping.get("title") or existing.get("title", ""),
        }
    else:
        merged = {
            "actress": mapping.get("actress", {}),
            "category": mapping.get("category", {}),
            "series": mapping.get("series", {}),
            "title": mapping.get("title", ""),
        }
    cursor.execute('''
        INSERT INTO translation_mappings (content_id, actress_json, category_json, series_json, title_json, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO UPDATE SET
            actress_json = excluded.actress_json,
            category_json = excluded.category_json,
            series_json = excluded.series_json,
            title_json = excluded.title_json,
            updated_at = CURRENT_TIMESTAMP
    ''', (content_id, json.dumps(merged["actress"]), json.dumps(merged["category"]),
          json.dumps(merged["series"]), json.dumps(merged["title"])))
    conn.commit()
    conn.close()
    return True

def get_all_translations(mapping_type: str) -> dict:
    """导出指定类型的全部映射。

    actress/category/series: { "原文": "译文" }
    title: { "content_id": "译文" }
    """
    field_map = {
        "actress": "actress_json",
        "category": "category_json",
        "series": "series_json",
        "title": "title_json"
    }
    field = field_map.get(mapping_type)
    if not field:
        return {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT content_id, {field} FROM translation_mappings")
    rows = cursor.fetchall()
    conn.close()
    result = {}
    for row in rows:
        parsed = json.loads(row[field] or "{}")
        if mapping_type == "title":
            # title: content_id → translated_title
            if parsed:
                result[row["content_id"]] = parsed
        else:
            # actress/category/series: original → translated
            # 跳过 global 前缀的 key，只导出普通 content_id 的映射
            cid = row["content_id"]
            if cid.startswith("_global:"):
                # 从 actress_json value 里取原文→译文的kv
                for k, v in parsed.items():
                    result[k] = v
            else:
                # per-content_id 的某个 field 的翻译也没有意义
                pass
    return result

def import_translations(mapping_type: str, data: dict) -> int:
    """批量导入翻译映射。

    actress/category/series: data = { "原文": "译文" }
    title: data = { "content_id": "译文" }
    """
    if mapping_type not in ("actress", "category", "series", "title"):
        return 0
    count = 0
    if mapping_type == "title":
        # data: { "content_id": "translated_title" }
        for cid, trans in data.items():
            upsert_translation(cid, {"title": trans})
            count += 1
    else:
        # data: { "original_name": "translated_name" }
        # 每个原文单独一行，key = "_global:{type}:{original_name}"
        for orig_name, trans_name in data.items():
            global_key = f"_global:{mapping_type}:{orig_name}"
            upsert_translation(global_key, {mapping_type: {orig_name: trans_name}})
            count += 1
    return count

def get_translation_count(mapping_type: str) -> int:
    """获取有翻译的条数统计。
    actress: 统计 actress:{id} 和 _global:actress:{name} 的 kv 对数量。
    category/series: 统计 global key 里的 kv 对数量。
    title: 统计有 title 翻译的 content_id 行数。
    """
    conn = get_db()
    cursor = conn.cursor()
    if mapping_type == "actress":
        # actress:{id} → {name: translated}
        cursor.execute(
            "SELECT actress_json FROM translation_mappings WHERE content_id LIKE 'actress:%'"
        )
        rows = cursor.fetchall()
        total = sum(len(json.loads(row["actress_json"] or "{}")) for row in rows)
        conn.close()
        return total
    elif mapping_type in ("category", "series"):
        # {type}:{id} 格式
        cursor.execute(
            f"SELECT {mapping_type}_json FROM translation_mappings WHERE content_id LIKE '{mapping_type}:%'"
        )
        rows = cursor.fetchall()
        total = sum(len(json.loads(row[mapping_type + "_json"] or "{}")) for row in rows)
        conn.close()
        return total
    else:  # title
        cursor.execute(
            "SELECT COUNT(*) FROM translation_mappings WHERE title_json IS NOT NULL AND title_json != '{}' AND title_json != '{ }' AND content_id NOT LIKE '_global:%'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count


# ==============================================
# 以下为原有数据库函数（保持不变）
# ==============================================

DB_PATH_ORIG = Path(__file__).parent.parent / "data" / "avdownloader.db"

def get_db_orig():
    conn = sqlite3.connect(DB_PATH_ORIG)
    conn.row_factory = sqlite3.Row
    return conn

def _migrate_download_tasks():
    """将 download_tasks.id 从 TEXT 迁移到 INTEGER（自动修复，只执行一次）"""
    try:
        conn = get_db_orig()
        cursor = conn.cursor()
        # 检查 id 列类型
        cursor.execute("PRAGMA table_info(download_tasks)")
        cols = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()
        if cols.get("id") == "TEXT":
            # 数据迁移：重建表
            conn2 = get_db_orig()
            cursor2 = conn2.cursor()
            cursor2.execute("ALTER TABLE download_tasks RENAME TO download_tasks_old")
            cursor2.execute('''
                CREATE TABLE download_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            cursor2.execute(f"INSERT INTO download_tasks (content_id, title, magnet, path, status, error_msg, created_at, updated_at) SELECT content_id, title, magnet, path, status, error_msg, created_at, updated_at FROM download_tasks_old")
            cursor2.execute("DROP TABLE download_tasks_old")
            conn2.commit()
            conn2.close()
    except Exception as e:
        pass  # 表不存在或有其他问题，跳过

def init_db():
    DB_PATH_ORIG.parent.mkdir(parents=True, exist_ok=True)
    init_translation_db()
    _migrate_download_tasks()
    conn = get_db_orig()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# Alias for existing code that imports from database.py
get_db = get_db_orig

# === Download Tasks ===

def create_download_task(content_id: str, title: str, magnet: str, path: Optional[str] = None) -> int:
    """创建下载任务"""
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
    """获取下载任务列表"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_task_status(task_id: int, status: str, error_msg: Optional[str] = None):
    """更新下载任务状态"""
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
    """删除下载任务"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM download_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# === Subscriptions ===

def add_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> int:
    """添加订阅"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subscriptions (actress_id, actress_name, auto_download, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, auto_download)
    )
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id

def get_subscriptions() -> list:
    """获取订阅列表"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_subscription(subscription_id: int):
    """删除订阅"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
    conn.commit()
    conn.close()

# === Logs ===

def add_log(level: str, message: str):
    """添加日志"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (level, message))
    conn.commit()
    conn.close()

def get_logs(limit: int = 100, level: Optional[str] = None) -> list:
    """获取日志"""
    conn = get_db_orig()
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
    conn = get_db_orig()
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
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM ignored_duplicates WHERE emby_item_id = ?", (emby_item_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# === Missing Summary ===

def save_missing_summary(actress_id: int, actress_name: str, total: int, missing: int, videos_json: str):
    """保存或更新缺失统计缓存"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    cursor.execute(
        "INSERT INTO actress_missing_summary (actress_id, actress_name, total_in_javinfo, missing_count, missing_videos_json, last_updated) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, total, missing, videos_json)
    )
    conn.commit()
    conn.close()

def get_all_missing_summaries() -> list:
    """获取所有缺失统计缓存"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary ORDER BY missing_count DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_missing_summary(actress_id: int) -> Optional[dict]:
    """获取指定演员的缺失统计"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actress_missing_summary WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
