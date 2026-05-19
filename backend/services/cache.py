from __future__ import annotations
import asyncio
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

# Default TTLs in seconds
DEFAULT_VIDEO_TTL = 86400       # 24h
DEFAULT_ENUM_TTL = 86400         # 24h
DEFAULT_SEARCH_TTL = 600         # 10min
DEFAULT_RESPONSE_TTL = 600       # 10min

_db_path: Optional[Path] = None
_response_locks: dict[str, asyncio.Lock] = {}
_metrics: dict[str, Any] = {}


def reset_metrics() -> None:
    global _metrics
    _metrics = {
        "video": {"hits": 0, "misses": 0},
        "search": {"hits": 0, "misses": 0},
        "enum": {"hits": 0, "misses": 0},
        "response": {"hits": 0, "misses": 0},
        "response_namespaces": {},
        "singleflight_waits": 0,
    }


reset_metrics()


def _record_metric(kind: str, hit: bool, namespace: str | None = None) -> None:
    bucket = _metrics.setdefault(kind, {"hits": 0, "misses": 0})
    bucket["hits" if hit else "misses"] = int(bucket.get("hits" if hit else "misses", 0)) + 1
    if kind == "response" and namespace:
        namespaces = _metrics.setdefault("response_namespaces", {})
        namespace_bucket = namespaces.setdefault(namespace, {"hits": 0, "misses": 0})
        namespace_bucket["hits" if hit else "misses"] = int(namespace_bucket.get("hits" if hit else "misses", 0)) + 1


def _record_singleflight_wait() -> None:
    _metrics["singleflight_waits"] = int(_metrics.get("singleflight_waits", 0)) + 1


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
    conn.execute("PRAGMA synchronous=NORMAL")
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
    hit = isinstance(data, dict)
    _record_metric("video", hit)
    return data if hit else None


def set_video(content_id: str, data: dict, ttl: int = DEFAULT_VIDEO_TTL) -> None:
    _set_json(f"video:{content_id}", data, ttl)


# === Search ===

def get_search(params: dict, page: int) -> Optional[dict]:
    key = _search_key(params, page)
    data = _get_json(key)
    hit = isinstance(data, dict)
    _record_metric("search", hit)
    return data if hit else None


def set_search(params: dict, page: int, data: dict, ttl: int = DEFAULT_SEARCH_TTL) -> None:
    key = _search_key(params, page)
    _set_json(key, data, ttl)


def _search_key(params: dict, page: int) -> str:
    stable = json.dumps(params, sort_keys=True, default=str)
    h = hashlib.sha256(stable.encode()).hexdigest()
    return f"search:{h}:{page}"


# === Response ===

def get_response(namespace: str, params: dict | None = None) -> Any | None:
    data = _get_json(_response_key(namespace, params or {}))
    _record_metric("response", data is not None, namespace=namespace)
    return data


def set_response(namespace: str, params: dict | None, data: Any, ttl: int = DEFAULT_RESPONSE_TTL) -> None:
    _set_json(_response_key(namespace, params or {}), data, ttl)


async def get_or_set_response(
    namespace: str,
    params: dict | None,
    producer: Callable[[], Awaitable[Any]],
    ttl: int = DEFAULT_RESPONSE_TTL,
) -> Any:
    cache_params = params or {}
    cached = get_response(namespace, cache_params)
    if cached is not None:
        return cached

    key = _response_key(namespace, cache_params)
    lock = _response_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _response_locks[key] = lock
    elif lock.locked():
        _record_singleflight_wait()

    async with lock:
        cached = get_response(namespace, cache_params)
        if cached is not None:
            return cached
        data = await producer()
        set_response(namespace, cache_params, data, ttl=ttl)
        return data


def _response_key(namespace: str, params: dict) -> str:
    stable = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    h = hashlib.sha256(stable.encode()).hexdigest()
    return f"response:{namespace}:{h}"


# === Enums ===

def get_enum_list(enum_type: str) -> Optional[list]:
    data = _get_json(f"enum:{enum_type}")
    hit = isinstance(data, list)
    _record_metric("enum", hit)
    return data if hit else None


def set_enum_list(enum_type: str, data: list, ttl: int = DEFAULT_ENUM_TTL) -> None:
    _set_json(f"enum:{enum_type}", data, ttl)


# === Stats ===

def get_stats() -> dict[str, Any]:
    now = time.time()
    by_kind = {"video": 0, "search": 0, "enum": 0, "response": 0, "other": 0}
    response_namespaces: dict[str, int] = {}
    expired_entries = 0
    total_entries = 0

    with _connect() as conn:
        rows = conn.execute("SELECT key, expires_at FROM cache_entries").fetchall()

    for key, expires_at in rows:
        total_entries += 1
        if expires_at <= now:
            expired_entries += 1
            continue
        kind = str(key).split(":", 1)[0]
        if kind == "response":
            by_kind["response"] += 1
            namespace = str(key).split(":", 2)[1] if ":" in str(key) else "unknown"
            response_namespaces[namespace] = response_namespaces.get(namespace, 0) + 1
        elif kind in by_kind:
            by_kind[kind] += 1
        else:
            by_kind["other"] += 1

    return {
        "total_entries": total_entries,
        "active_entries": total_entries - expired_entries,
        "expired_entries": expired_entries,
        "by_kind": by_kind,
        "response_namespaces": dict(sorted(response_namespaces.items())),
        "metrics": {
            "video": dict(_metrics["video"]),
            "search": dict(_metrics["search"]),
            "enum": dict(_metrics["enum"]),
            "response": dict(_metrics["response"]),
            "response_namespaces": {
                namespace: dict(values)
                for namespace, values in sorted(_metrics.get("response_namespaces", {}).items())
            },
            "singleflight_waits": int(_metrics.get("singleflight_waits", 0)),
        },
        "singleflight_locks": len(_response_locks),
    }


# === Purge ===

def purge_video_cache() -> int:
    """清除所有 video 和 search 缓存，返回清除数量"""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM cache_entries WHERE key LIKE 'video:%' OR key LIKE 'search:%'"
        )
        return cursor.rowcount


def purge_response_cache() -> int:
    """清除最终响应缓存，返回清除数量"""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM cache_entries WHERE key LIKE 'response:%'")
        return cursor.rowcount


def purge_enum_cache() -> int:
    """清除枚举原始缓存和对应的最终响应缓存，返回清除数量"""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM cache_entries WHERE key LIKE 'enum:%' OR key LIKE 'response:%'"
        )
        return cursor.rowcount


def purge_all() -> int:
    """清除所有缓存"""
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
        conn.execute("DELETE FROM cache_entries")
        return int(count)
