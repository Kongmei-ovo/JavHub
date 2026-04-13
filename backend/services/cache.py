from __future__ import annotations
import hashlib
import json
from pathlib import Path
from diskcache import Cache
from typing import Any, Optional

# Default TTLs in seconds
DEFAULT_VIDEO_TTL = 86400       # 24h
DEFAULT_STATS_TTL = 3600        # 1h
DEFAULT_ENUM_TTL = 86400         # 24h
DEFAULT_SEARCH_TTL = 600         # 10min

_cache: Optional[Cache] = None


def _get_cache() -> Cache:
    global _cache
    if _cache is None:
        cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _cache = Cache(str(cache_dir), size_limit=5 * 1024 * 1024 * 1024)  # 5GB
    return _cache


# === Video ===

def get_video(content_id: str) -> Optional[dict]:
    return _get_cache().get(f"video:{content_id}")


def set_video(content_id: str, data: dict, ttl: int = DEFAULT_VIDEO_TTL) -> None:
    _get_cache().set(f"video:{content_id}", data, expire=ttl)


# === Search ===

def get_search(params: dict, page: int) -> Optional[dict]:
    key = _search_key(params, page)
    return _get_cache().get(key)


def set_search(params: dict, page: int, data: dict, ttl: int = DEFAULT_SEARCH_TTL) -> None:
    key = _search_key(params, page)
    _get_cache().set(key, data, expire=ttl)


def _search_key(params: dict, page: int) -> str:
    stable = json.dumps(params, sort_keys=True, default=str)
    h = hashlib.md5(stable.encode()).hexdigest()
    return f"search:{h}:{page}"


# === Category Stats ===

def get_category_stats() -> Optional[list]:
    return _get_cache().get("category:stats")


def set_category_stats(data: list, ttl: int = DEFAULT_STATS_TTL) -> None:
    _get_cache().set("category:stats", data, expire=ttl)


# === Enums ===

def get_enum_list(enum_type: str) -> Optional[list]:
    return _get_cache().get(f"enum:{enum_type}")


def set_enum_list(enum_type: str, data: list, ttl: int = DEFAULT_ENUM_TTL) -> None:
    _get_cache().set(f"enum:{enum_type}", data, expire=ttl)


# === Purge ===

def purge_video_cache() -> int:
    """清除所有 video 和 search 缓存，返回清除数量"""
    cache = _get_cache()
    count = 0
    for key in list(cache.iterkeys()):
        if key.startswith("video:") or key.startswith("search:"):
            del cache[key]
            count += 1
    return count


def purge_all() -> int:
    """清除所有缓存"""
    count = len(_get_cache())
    _get_cache().clear()
    return count
