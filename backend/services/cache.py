from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

# Default TTLs in seconds
DEFAULT_VIDEO_TTL = 86400       # 24h
DEFAULT_ENUM_TTL = 86400         # 24h
DEFAULT_SEARCH_TTL = 600         # 10min

_db_path: Optional[Path] = None


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _db_path = cache_dir / "cache.sqlite3"
        _init_db(_db_path)
    return _db_path


def _connect() -> sqlite3.Connection:
    path = _get_db_path()
    _init_db(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_entries_expires_at ON cache_entries(expires_at)")


def _get_json(key: str) -> Any | None:
    now = time.time()
    with _connect() as conn:
        row = conn.execute(
            "SELECT value, expires_at FROM cache_entries WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if expires_at <= now:
            conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            return None
    return json.loads(value)


def _set_json(key: str, data: Any, ttl: int) -> None:
    expires_at = time.time() + max(0, ttl)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO cache_entries (key, value, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                expires_at = excluded.expires_at
            """,
            (key, body, expires_at),
        )


# === Video ===

def get_video(content_id: str) -> Optional[dict]:
    data = _get_json(f"video:{content_id}")
    return data if isinstance(data, dict) else None


def set_video(content_id: str, data: dict, ttl: int = DEFAULT_VIDEO_TTL) -> None:
    _set_json(f"video:{content_id}", data, ttl)


# === Search ===

def get_search(params: dict, page: int) -> Optional[dict]:
    key = _search_key(params, page)
    data = _get_json(key)
    return data if isinstance(data, dict) else None


def set_search(params: dict, page: int, data: dict, ttl: int = DEFAULT_SEARCH_TTL) -> None:
    key = _search_key(params, page)
    _set_json(key, data, ttl)


def _search_key(params: dict, page: int) -> str:
    stable = json.dumps(params, sort_keys=True, default=str)
    h = hashlib.sha256(stable.encode()).hexdigest()
    return f"search:{h}:{page}"


# === Enums ===

def get_enum_list(enum_type: str) -> Optional[list]:
    data = _get_json(f"enum:{enum_type}")
    return data if isinstance(data, list) else None


def set_enum_list(enum_type: str, data: list, ttl: int = DEFAULT_ENUM_TTL) -> None:
    _set_json(f"enum:{enum_type}", data, ttl)


# === Purge ===

def purge_video_cache() -> int:
    """清除所有 video 和 search 缓存，返回清除数量"""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM cache_entries WHERE key LIKE 'video:%' OR key LIKE 'search:%'"
        )
        return cursor.rowcount


def purge_all() -> int:
    """清除所有缓存"""
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
        conn.execute("DELETE FROM cache_entries")
        return int(count)
