from __future__ import annotations
import asyncio
from dataclasses import dataclass
import hashlib
import json
import os
import time
from typing import Any, Awaitable, Callable, Optional

# Default TTLs in seconds
DEFAULT_VIDEO_TTL = 86400       # 24h
DEFAULT_ENUM_TTL = 86400         # 24h
DEFAULT_SEARCH_TTL = 600         # 10min
DEFAULT_RESPONSE_TTL = 600       # 10min

_metrics: dict[str, Any] = {}
_backend: Any | None = None


@dataclass
class _ResponseLockEntry:
    lock: asyncio.Lock
    users: int = 0


_response_locks: dict[str, _ResponseLockEntry] = {}


class RedisCacheBackend:
    name = "redis"

    def __init__(self) -> None:
        url = os.getenv("JAVHUB_REDIS_URL", "").strip()
        if not url:
            raise RuntimeError("JAVHUB_REDIS_URL is required when JAVHUB_CACHE_BACKEND=redis")
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "Redis cache backend selected but redis package is not installed. "
                "Install redis and set JAVHUB_REDIS_URL."
            ) from exc
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = os.getenv("JAVHUB_REDIS_PREFIX", "javhub-cache").strip() or "javhub-cache"

    def get_json(self, key: str) -> Any | None:
        value = self._client.get(self._redis_key(key))
        if value is None:
            return None
        return json.loads(value)

    def set_json(self, key: str, data: Any, ttl: int) -> None:
        redis_key = self._redis_key(key)
        if ttl <= 0:
            self._client.delete(redis_key)
            return
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
        self._client.set(redis_key, body, ex=max(1, int(ttl)))

    def get_entry_stats(self) -> dict[str, Any]:
        by_kind = {"video": 0, "search": 0, "enum": 0, "response": 0, "other": 0}
        response_namespaces: dict[str, int] = {}
        total_entries = 0
        expired_entries = 0

        for raw_key in self._scan("*"):
            key = self._local_key(raw_key)
            if key is None:
                continue
            total_entries += 1
            ttl = self._client.ttl(raw_key)
            if ttl == -2:
                expired_entries += 1
                continue
            _count_cache_key(key, by_kind, response_namespaces)

        return _entry_stats(total_entries, expired_entries, by_kind, response_namespaces)

    def purge_video_cache(self) -> int:
        return self._delete_patterns("video:*", "search:*")

    def purge_response_cache(self) -> int:
        return self._delete_patterns("response:*")

    def purge_enum_cache(self) -> int:
        return self._delete_patterns("enum:*", "response:*")

    def purge_all(self) -> int:
        return self._delete_patterns("*")

    def _redis_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def _local_key(self, raw_key: Any) -> str | None:
        key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
        prefix = f"{self._prefix}:"
        if not key.startswith(prefix):
            return None
        return key[len(prefix):]

    def _scan(self, pattern: str) -> list[Any]:
        return list(self._client.scan_iter(match=self._redis_key(pattern), count=1000))

    def _delete_patterns(self, *patterns: str) -> int:
        keys: list[Any] = []
        seen: set[str] = set()
        for pattern in patterns:
            for raw_key in self._scan(pattern):
                marker = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
                if marker not in seen:
                    seen.add(marker)
                    keys.append(raw_key)
        if not keys:
            return 0
        return int(self._client.delete(*keys) or 0)


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


def reset_backend() -> None:
    global _backend
    _backend = None
    _response_locks.clear()


def get_backend() -> Any:
    global _backend
    if _backend is None:
        backend_name = os.getenv("JAVHUB_CACHE_BACKEND", "redis").strip().lower() or "redis"
        if backend_name == "redis":
            _backend = RedisCacheBackend()
        else:
            raise RuntimeError(f"Unsupported JAVHUB_CACHE_BACKEND: {backend_name}")
    return _backend


def get_backend_name() -> str:
    return str(get_backend().name)


def _record_metric(kind: str, hit: bool, namespace: str | None = None) -> None:
    bucket = _metrics.setdefault(kind, {"hits": 0, "misses": 0})
    bucket["hits" if hit else "misses"] = int(bucket.get("hits" if hit else "misses", 0)) + 1
    if kind == "response" and namespace:
        namespaces = _metrics.setdefault("response_namespaces", {})
        namespace_bucket = namespaces.setdefault(namespace, {"hits": 0, "misses": 0})
        namespace_bucket["hits" if hit else "misses"] = int(namespace_bucket.get("hits" if hit else "misses", 0)) + 1


def _record_singleflight_wait() -> None:
    _metrics["singleflight_waits"] = int(_metrics.get("singleflight_waits", 0)) + 1


def _get_json(key: str) -> Any | None:
    return get_backend().get_json(key)


def _set_json(key: str, data: Any, ttl: int) -> None:
    get_backend().set_json(key, data, ttl)


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
    lock_entry = _response_locks.get(key)
    if lock_entry is None:
        lock_entry = _ResponseLockEntry(lock=asyncio.Lock())
        _response_locks[key] = lock_entry
    elif lock_entry.lock.locked():
        _record_singleflight_wait()

    lock_entry.users += 1
    try:
        async with lock_entry.lock:
            cached = get_response(namespace, cache_params)
            if cached is not None:
                return cached
            data = await producer()
            set_response(namespace, cache_params, data, ttl=ttl)
            return data
    finally:
        lock_entry.users -= 1
        if lock_entry.users == 0 and not lock_entry.lock.locked():
            _response_locks.pop(key, None)


def _response_key(namespace: str, params: dict) -> str:
    stable = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    h = hashlib.sha256(stable.encode()).hexdigest()
    return f"response:{namespace}:{h}"


def _count_cache_key(key: Any, by_kind: dict[str, int], response_namespaces: dict[str, int]) -> None:
    key_text = str(key)
    kind = key_text.split(":", 1)[0]
    if kind == "response":
        by_kind["response"] += 1
        parts = key_text.split(":", 2)
        namespace = parts[1] if len(parts) > 1 else "unknown"
        response_namespaces[namespace] = response_namespaces.get(namespace, 0) + 1
    elif kind in by_kind:
        by_kind[kind] += 1
    else:
        by_kind["other"] += 1


def _entry_stats(
    total_entries: int,
    expired_entries: int,
    by_kind: dict[str, int],
    response_namespaces: dict[str, int],
) -> dict[str, Any]:
    return {
        "total_entries": total_entries,
        "active_entries": total_entries - expired_entries,
        "expired_entries": expired_entries,
        "by_kind": by_kind,
        "response_namespaces": dict(sorted(response_namespaces.items())),
    }


def _metrics_stats() -> dict[str, Any]:
    return {
        "video": dict(_metrics["video"]),
        "search": dict(_metrics["search"]),
        "enum": dict(_metrics["enum"]),
        "response": dict(_metrics["response"]),
        "response_namespaces": {
            namespace: dict(values)
            for namespace, values in sorted(_metrics.get("response_namespaces", {}).items())
        },
        "singleflight_waits": int(_metrics.get("singleflight_waits", 0)),
    }


# === Enums ===

def get_enum_list(enum_type: str) -> Optional[list]:
    data = _get_json(f"enum:{enum_type}")
    hit = isinstance(data, list)
    _record_metric("enum", hit)
    return data if hit else None


def set_enum_list(enum_type: str, data: list, ttl: int = DEFAULT_ENUM_TTL) -> None:
    _set_json(f"enum:{enum_type}", data, ttl)


# === Data Generations ===

def get_data_generation(namespace: str) -> int:
    data = _get_json(_generation_key(namespace))
    return int(data) if isinstance(data, int) else 0


def set_data_generation(namespace: str, generation: int, ttl: int = DEFAULT_ENUM_TTL) -> None:
    _set_json(_generation_key(namespace), int(generation), ttl)


def _generation_key(namespace: str) -> str:
    return f"generation:{namespace}"


# === Stats ===

def get_stats() -> dict[str, Any]:
    stats = get_backend().get_entry_stats()
    stats["backend"] = get_backend_name()
    stats["metrics"] = _metrics_stats()
    stats["singleflight_locks"] = len(_response_locks)
    return stats


# === Purge ===

def purge_video_cache() -> int:
    """清除所有 video 和 search 缓存，返回清除数量"""
    return int(get_backend().purge_video_cache())


def purge_response_cache() -> int:
    """清除最终响应缓存，返回清除数量"""
    return int(get_backend().purge_response_cache())


def purge_enum_cache() -> int:
    """清除枚举原始缓存和对应的最终响应缓存，返回清除数量"""
    return int(get_backend().purge_enum_cache())


def purge_all() -> int:
    """清除所有缓存"""
    return int(get_backend().purge_all())
