"""翻译映射数据库层"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "avdownloader.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _get_translation_db():
    """翻译映射数据库连接"""
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
    conn = _get_translation_db()
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
    conn = _get_translation_db()
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
    conn = _get_translation_db()
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
    conn = _get_translation_db()
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
    conn = _get_translation_db()
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

    # Inventory tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            actor_id INTEGER,
            snapshot_key TEXT,
            status TEXT DEFAULT 'pending',
            error_msg TEXT,
            progress INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    ''')

    # 迁移：为已存在的表添加 snapshot_key 和 progress 列
    try:
        cursor.execute("ALTER TABLE inventory_jobs ADD COLUMN snapshot_key TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE inventory_jobs ADD COLUMN progress INTEGER DEFAULT 0")
    except Exception:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_actors (
            actress_id INTEGER PRIMARY KEY,
            actress_name TEXT NOT NULL,
            normalized_id INTEGER,
            primary_name TEXT,
            total_videos INTEGER DEFAULT 0,
            missing_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_videos (
            content_id TEXT PRIMARY KEY,
            emby_item_id TEXT NOT NULL,
            actress_id INTEGER NOT NULL,
            title TEXT,
            release_date TEXT,
            jacket_thumb_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS missing_videos (
            content_id TEXT PRIMARY KEY,
            actress_id INTEGER NOT NULL,
            title TEXT,
            release_date TEXT,
            jacket_thumb_url TEXT,
            source TEXT DEFAULT 'javinfo',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exempt_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT UNIQUE NOT NULL,
            actress_id INTEGER,
            reason TEXT,
            created_by TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actor_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_id INTEGER NOT NULL,
            canonical_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emby_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_key TEXT NOT NULL,
            actress_id INTEGER NOT NULL,
            actress_name TEXT NOT NULL,
            emby_item_id TEXT NOT NULL,
            title TEXT,
            filename TEXT,
            collected_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emby_actors (
            actress_id INTEGER PRIMARY KEY,
            actress_name TEXT NOT NULL,
            total_videos INTEGER DEFAULT 0,
            image_tag TEXT,
            snapshot_key TEXT,
            updated_at TEXT
        )
    ''')

    # 迁移：添加 image_tag 列
    try:
        cursor.execute("ALTER TABLE emby_actors ADD COLUMN image_tag TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()

# get_db removed - use explicit get_db_orig() or _get_translation_db()

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

# === Inventory Jobs ===
def add_inventory_job(job_type: str, actor_id: Optional[int] = None, snapshot_key: Optional[str] = None) -> int:
    """创建对比作业记录"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventory_jobs (job_type, actor_id, snapshot_key, status, created_at) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
        (job_type, actor_id, snapshot_key)
    )
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id

def update_inventory_job(job_id: int, status: str, error_msg: Optional[str] = None, snapshot_key: Optional[str] = None):
    """更新作业状态"""
    conn = get_db_orig()
    cursor = conn.cursor()
    if snapshot_key is not None:
        cursor.execute(
            "UPDATE inventory_jobs SET status = ?, error_msg = ?, snapshot_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, error_msg, snapshot_key, job_id)
        )
    elif error_msg:
        cursor.execute(
            "UPDATE inventory_jobs SET status = ?, error_msg = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, error_msg, job_id)
        )
    else:
        cursor.execute(
            "UPDATE inventory_jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, job_id)
        )
    conn.commit()
    conn.close()

def update_inventory_progress(job_id: int, progress: int):
    """更新作业进度"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory_jobs SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (progress, job_id)
    )
    conn.commit()
    conn.close()

def get_inventory_jobs(limit: int = 50) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_inventory_job(job_id: int) -> Optional[dict]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# === Inventory Actors ===
def upsert_inventory_actor(actress_id: int, actress_name: str, normalized_id: Optional[int] = None, primary_name: Optional[str] = None) -> int:
    """插入或更新库存演员"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory_actors (actress_id, actress_name, normalized_id, primary_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(actress_id) DO UPDATE SET
            actress_name = excluded.actress_name,
            normalized_id = COALESCE(excluded.normalized_id, inventory_actors.normalized_id),
            primary_name = COALESCE(excluded.primary_name, inventory_actors.primary_name),
            updated_at = CURRENT_TIMESTAMP
    ''', (actress_id, actress_name, normalized_id, primary_name))
    conn.commit()
    conn.close()
    return actress_id

def get_inventory_actors() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_actors ORDER BY actress_name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_inventory_actor(actress_id: int) -> Optional[dict]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_actors WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_inventory_actor_stats(actress_id: int, total_videos: int, missing_count: int):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
        (total_videos, missing_count, actress_id)
    )
    conn.commit()
    conn.close()

# === Inventory Videos ===
def upsert_inventory_video(content_id: str, emby_item_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory_videos (content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO UPDATE SET
            emby_item_id = excluded.emby_item_id,
            actress_id = excluded.actress_id,
            title = excluded.title,
            release_date = excluded.release_date,
            jacket_thumb_url = excluded.jacket_thumb_url,
            updated_at = CURRENT_TIMESTAMP
    ''', (content_id, emby_item_id, actress_id, title, release_date, jacket_thumb_url))
    conn.commit()
    conn.close()
    return actress_id

def get_inventory_videos(actress_id: int) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# === Missing Videos ===
def add_missing_video(content_id: str, actress_id: int, title: str, release_date: Optional[str], jacket_thumb_url: Optional[str]) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO missing_videos (content_id, actress_id, title, release_date, jacket_thumb_url, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO NOTHING
    ''', (content_id, actress_id, title, release_date, jacket_thumb_url))
    conn.commit()
    conn.close()
    return cursor.lastrowid or 0

def get_missing_videos(actress_id: int) -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM missing_videos WHERE actress_id = ? ORDER BY release_date DESC", (actress_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_missing_videos() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM missing_videos ORDER BY release_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_missing_video(content_id: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM missing_videos WHERE content_id = ?", (content_id,))
    conn.commit()
    conn.close()

def get_missing_count_by_actress(actress_id: int) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM missing_videos WHERE actress_id = ?", (actress_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# === Exempt Videos ===
def add_exempt_video(content_id: str, actress_id: int, reason: str, created_by: str = "manual") -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO exempt_videos (content_id, actress_id, reason, created_by, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(content_id) DO UPDATE SET
            reason = excluded.reason,
            actress_id = excluded.actress_id
    ''', (content_id, actress_id, reason, created_by))
    conn.commit()
    conn.close()
    return cursor.lastrowid or 0

def get_exempt_videos() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exempt_videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_exempt_video(content_id: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exempt_videos WHERE content_id = ?", (content_id,))
    conn.commit()
    conn.close()

def is_video_exempt(content_id: str) -> bool:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM exempt_videos WHERE content_id = ?", (content_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# === Actor Aliases ===
def add_actor_alias(alias_id: int, canonical_id: int) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO actor_aliases (alias_id, canonical_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (alias_id, canonical_id)
    )
    conn.commit()
    conn.close()
    return alias_id

def get_actor_aliases() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actor_aliases")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_canonical_actress_id(actress_id: int) -> int:
    """递归查找规范演员ID"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT canonical_id FROM actor_aliases WHERE alias_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_canonical_actress_id(row["canonical_id"])
    return actress_id

def set_actor_primary_name(actress_id: int, primary_name: str):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory_actors SET primary_name = ? WHERE actress_id = ?", (primary_name, actress_id))
    conn.commit()
    conn.close()

def reassign_actress_movies(from_actress_id: int, to_actress_id: int):
    """将一个演员的所有电影转移到另一个演员（批量合并）"""
    conn = get_db_orig()
    cursor = conn.cursor()

    # 1. 转移 inventory_videos
    cursor.execute(
        "UPDATE inventory_videos SET actress_id = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
        (to_actress_id, from_actress_id)
    )

    # 2. 转移 missing_videos
    cursor.execute(
        "UPDATE missing_videos SET actress_id = ? WHERE actress_id = ?",
        (to_actress_id, from_actress_id)
    )

    # 3. 重建统计（inventory_actors）
    # 被合并方的统计合并到目标方
    for table, id_field in [("inventory_videos", "actress_id"), ("missing_videos", "actress_id")]:
        cursor.execute(
            f"SELECT COUNT(*) as cnt FROM {table} WHERE actress_id = ?",
            (to_actress_id,)
        )
        new_total = cursor.fetchone()["cnt"]
        cursor.execute(
            f"SELECT COUNT(*) as cnt FROM missing_videos WHERE actress_id = ?",
            (to_actress_id,)
        )
        new_missing = cursor.fetchone()["cnt"]
        cursor.execute(
            "UPDATE inventory_actors SET total_videos = ?, missing_count = ?, updated_at = CURRENT_TIMESTAMP WHERE actress_id = ?",
            (new_total, new_missing, to_actress_id)
        )

    # 4. 从 emby_actors 删除被合并方
    cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (from_actress_id,))

    conn.commit()
    conn.close()
    return True

def delete_emby_actor(actress_id: int):
    """从 emby_actors 表删除演员"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emby_actors WHERE actress_id = ?", (actress_id,))
    conn.commit()
    conn.close()

def find_similar_actresses(snapshot_key: str, name: str = None, threshold: float = 0.6) -> list:
    """查找名字相似的演员（用于发现重复演员）"""
    import difflib
    result = get_snapshot_actors(snapshot_key, page_size=10000)
    all_actors = result["data"]
    if name:
        candidates = [a for a in all_actors if name.lower() in a["actress_name"].lower()]
    else:
        candidates = all_actors

    similar = []
    checked = set()
    for i, a in enumerate(candidates):
        for j, b in enumerate(candidates):
            if i >= j or b["actress_id"] in checked:
                continue
            ratio = difflib.SequenceMatcher(None, a["actress_name"].lower(), b["actress_name"].lower()).ratio()
            if ratio >= threshold and a["actress_id"] != b["actress_id"]:
                similar.append({
                    "actor_a": a,
                    "actor_b": b,
                    "similarity": round(ratio, 2)
                })
                checked.add(b["actress_id"])
    # 按相似度降序
    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar
    conn.commit()
    conn.close()

def get_actor_primary_name(actress_id: int) -> Optional[str]:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT primary_name FROM inventory_actors WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return row["primary_name"] if row else None

# === Emby Snapshots ===
import hashlib
import time

def create_snapshot_key() -> str:
    """生成新的快照key"""
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

def clear_snapshot(snapshot_key: str):
    """清除指定快照的数据"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
    cursor.execute("DELETE FROM emby_actors WHERE snapshot_key = ?", (snapshot_key,))
    conn.commit()
    conn.close()

def save_emvy_snapshot(snapshot_key: str, actress_id: int, actress_name: str, emby_item_id: str, title: str, filename: str):
    """保存单个影片到快照"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO emby_snapshots (snapshot_key, actress_id, actress_name, emby_item_id, title, filename, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (snapshot_key, actress_id, actress_name, emby_item_id, title, filename))
    conn.commit()
    conn.close()

def save_emby_actors_snapshot(snapshot_key: str, actors: list):
    """批量保存演员快照（带视频计数和头像标签）"""
    conn = get_db_orig()
    cursor = conn.cursor()
    for actor in actors:
        cursor.execute('''
            INSERT INTO emby_actors (actress_id, actress_name, total_videos, image_tag, snapshot_key, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(actress_id) DO UPDATE SET
                actress_name = excluded.actress_name,
                total_videos = excluded.total_videos,
                image_tag = COALESCE(excluded.image_tag, emby_actors.image_tag),
                snapshot_key = excluded.snapshot_key,
                updated_at = CURRENT_TIMESTAMP
        ''', (actor["actress_id"], actor["actress_name"], actor["video_count"], actor.get("image_tag"), snapshot_key))
    conn.commit()
    conn.close()

def get_latest_snapshot_key() -> Optional[str]:
    """获取最新的快照key"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT snapshot_key FROM emby_actors ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row["snapshot_key"] if row else None

def get_snapshot_actors(snapshot_key: str, search: str = None, sort_by: str = None, sort_order: str = "asc",
                          page: int = 1, page_size: int = 50) -> dict:
    """获取指定快照的演员列表，支持搜索、排序、分页"""
    conn = get_db_orig()
    cursor = conn.cursor()

    # 构建 WHERE 条件
    where_clause = "WHERE snapshot_key = ?"
    params = [snapshot_key]

    if search:
        where_clause += " AND actress_name LIKE ?"
        params.append(f"%{search}%")

    # 获取总数
    count_sql = f"SELECT COUNT(*) as cnt FROM emby_actors {where_clause}"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()["cnt"]

    # 构建 ORDER BY
    order_col = "actress_name"
    if sort_by == "total_videos":
        order_col = "total_videos"
    elif sort_by == "missing_count":
        # missing_count 来自 inventory_actors 表，这里按 actress_name 排序后由调用方处理
        order_col = "actress_name"

    order_dir = "ASC" if sort_order == "asc" else "DESC"
    order_clause = f"ORDER BY {order_col} {order_dir}"

    # 分页
    offset = (page - 1) * page_size
    limit = page_size

    sql = f"SELECT * FROM emby_actors {where_clause} {order_clause} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return {
        "data": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
    }

def get_snapshot_videos(snapshot_key: str, actress_id: int) -> list:
    """获取指定快照中某演员的所有影片"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM emby_snapshots WHERE snapshot_key = ? AND actress_id = ? ORDER BY title",
        (snapshot_key, actress_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_snapshot_filenames(snapshot_key: str) -> set:
    """获取指定快照中所有影片的filename集合"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM emby_snapshots WHERE snapshot_key = ?", (snapshot_key,))
    rows = cursor.fetchall()
    conn.close()
    return {row["filename"] for row in rows if row["filename"]}
