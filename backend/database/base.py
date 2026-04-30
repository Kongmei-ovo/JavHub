"""数据库基础连接和初始化"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# 关键：database/ 在 backend/ 下，比原 database.py 深一层，所以是 parent.parent.parent
DB_PATH = Path(__file__).parent.parent.parent / "data" / "avdownloader.db"


def get_db_orig():
    """主数据库连接（向后兼容原 get_db_orig）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db():
    """数据库连接上下文管理器，自动 commit/rollback/close"""
    conn = get_db_orig()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_download_tasks():
    """将 download_tasks.id 从 TEXT 迁移到 INTEGER（自动修复，只执行一次）"""
    try:
        conn = get_db_orig()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(download_tasks)")
        cols = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()
        if cols.get("id") == "TEXT":
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
            cursor2.execute(
                "INSERT INTO download_tasks (content_id, title, magnet, path, status, error_msg, created_at, updated_at) "
                "SELECT content_id, title, magnet, path, status, error_msg, created_at, updated_at FROM download_tasks_old"
            )
            cursor2.execute("DROP TABLE download_tasks_old")
            conn2.commit()
            conn2.close()
    except Exception:
        pass


def init_db():
    """初始化所有表结构"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    from database.translation import init_translation_db
    init_translation_db()
    from database.favorite import init_favorite_db
    init_favorite_db()
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

    # Inventory jobs
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
    try:
        cursor.execute("ALTER TABLE inventory_jobs ADD COLUMN snapshot_key TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE inventory_jobs ADD COLUMN progress INTEGER DEFAULT 0")
    except Exception:
        pass

    # Inventory actors
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

    # Inventory videos
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

    # Missing videos
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

    # Exempt videos
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

    # Actor aliases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actor_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_id INTEGER NOT NULL,
            canonical_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Emby snapshots (movies)
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

    # Emby actors (snapshot metadata)
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
    try:
        cursor.execute("ALTER TABLE emby_actors ADD COLUMN image_tag TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()

    _migrate_subscriptions()
    _create_indexes()


def _create_indexes():
    """创建常用查询索引"""
    conn = get_db_orig()
    cursor = conn.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_download_tasks_status ON download_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_download_tasks_content_id ON download_tasks(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_missing_videos_actress_id ON missing_videos(actress_id)",
        "CREATE INDEX IF NOT EXISTS idx_emby_snapshots_snapshot_key ON emby_snapshots(snapshot_key, actress_id)",
        "CREATE INDEX IF NOT EXISTS idx_actor_aliases_alias_id ON actor_aliases(alias_id)",
        "CREATE INDEX IF NOT EXISTS idx_actor_aliases_canonical_id ON actor_aliases(canonical_id)",
        "CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_jobs_status ON inventory_jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_jobs_job_type ON inventory_jobs(job_type)",
    ]
    for sql in indexes:
        try:
            cursor.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def _migrate_subscriptions():
    """迁移 subscriptions 表结构"""
    conn = get_db_orig()
    cursor = conn.cursor()
    # 检查 last_check 列是否存在
    cursor.execute("PRAGMA table_info(subscriptions)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "last_check" not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN last_check TEXT")
    if "last_found" not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN last_found TEXT")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_actress_id ON subscriptions(actress_id)")
    conn.commit()
    conn.close()
