from __future__ import annotations
import asyncio
from dataclasses import dataclass
import hashlib
import json
import os
import inspect
import threading
import time
from typing import Any, Awaitable, Callable, Optional

from modules.loop_client_pool import LoopClientPool

# Default TTLs in seconds
DEFAULT_VIDEO_TTL = 86400       # 24h
DEFAULT_ENUM_TTL = 86400         # 24h
DEFAULT_SEARCH_TTL = 600         # 10min
DEFAULT_RESPONSE_TTL = 600       # 10min

_metrics: dict[str, Any] = {}
_backend: Any | None = None
_GENERATION_LOCAL_TTL = 1.0
_RESPONSE_LOCAL_TTL = 2.0
_RESPONSE_LOCAL_MAX = 1024
_generation_cache: dict[str, tuple[float, int]] = {}
_response_local_cache: dict[str, tuple[float, Any]] = {}


@dataclass
class _ResponseLockEntry:
    lock: asyncio.Lock
    bypass_task: asyncio.Task[Any] | None = None
    users: int = 0


_response_locks: dict[tuple[asyncio.AbstractEventLoop, str], _ResponseLockEntry] = {}


class _RedisAsyncClientAdapter:
    def __init__(self, client: Any) -> None:
        self._client = client
        self.is_closed = False

    async def get(self, key: str) -> Any:
        return await self._client.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> Any:
        return await self._client.set(key, value, ex=ex)

    async def delete(self, key: str) -> Any:
        return await self._client.delete(key)

    async def aclose(self) -> None:
        closer = getattr(self._client, "aclose", None) or getattr(self._client, "close", None)
        if callable(closer):
            result = closer()
            if inspect.isawaitable(result):
                await result
        self.is_closed = True


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
        self._url = url
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._async_pool: LoopClientPool[_RedisAsyncClientAdapter] | None | bool = None
        self._async_pool_lock = threading.Lock()
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

    async def aget_json(self, key: str) -> Any | None:
        pool = self._get_async_pool()
        if pool is None:
            return await asyncio.to_thread(self.get_json, key)
        async with pool.lease() as client:
            value = await client.get(self._redis_key(key))
        if value is None:
            return None
        return json.loads(value)

    async def aset_json(self, key: str, data: Any, ttl: int) -> None:
        pool = self._get_async_pool()
        if pool is None:
            await asyncio.to_thread(self.set_json, key, data, ttl)
            return
        redis_key = self._redis_key(key)
        async with pool.lease() as client:
            if ttl <= 0:
                await client.delete(redis_key)
                return
            body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
            await client.set(redis_key, body, ex=max(1, int(ttl)))

    async def aclose(self) -> None:
        with self._async_pool_lock:
            pool = self._async_pool
        if isinstance(pool, LoopClientPool):
            await pool.close_all()

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

    def _get_async_pool(self) -> LoopClientPool[_RedisAsyncClientAdapter] | None:
        with self._async_pool_lock:
            if self._async_pool is False:
                return None
            if self._async_pool is not None:
                return self._async_pool
            try:
                from redis import asyncio as redis_asyncio
            except (ImportError, AttributeError):
                self._async_pool = False
                return None
            self._async_pool = LoopClientPool(
                lambda: _RedisAsyncClientAdapter(
                    redis_asyncio.Redis.from_url(self._url, decode_responses=True)
                )
            )
            return self._async_pool

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
    _generation_cache.clear()
    _response_local_cache.clear()


async def close_backend() -> None:
    backend = _backend
    closer = getattr(backend, "aclose", None)
    if callable(closer):
        await closer()


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


async def _get_json_async(key: str) -> Any | None:
    backend = get_backend()
    getter = getattr(backend, "aget_json", None)
    if callable(getter):
        return await getter(key)
    return await asyncio.to_thread(backend.get_json, key)


async def _set_json_async(key: str, data: Any, ttl: int) -> None:
    backend = get_backend()
    setter = getattr(backend, "aset_json", None)
    if callable(setter):
        await setter(key, data, ttl)
        return
    await asyncio.to_thread(backend.set_json, key, data, ttl)


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
    key = _response_key(namespace, params or {})
    data = _get_local_response(key)
    if data is None:
        data = _get_json(key)
        if data is not None:
            _set_local_response(key, data)
    _record_metric("response", data is not None, namespace=namespace)
    return data


def set_response(namespace: str, params: dict | None, data: Any, ttl: int = DEFAULT_RESPONSE_TTL) -> None:
    key = _response_key(namespace, params or {})
    _set_json(key, data, ttl)
    if ttl <= 0:
        _response_local_cache.pop(key, None)
    else:
        _set_local_response(key, data, ttl=ttl)


async def get_response_async(namespace: str, params: dict | None = None) -> Any | None:
    key = _response_key(namespace, params or {})
    data = _get_local_response(key)
    if data is None:
        data = await _get_json_async(key)
        if data is not None:
            _set_local_response(key, data)
    _record_metric("response", data is not None, namespace=namespace)
    return data


async def set_response_async(
    namespace: str,
    params: dict | None,
    data: Any,
    ttl: int = DEFAULT_RESPONSE_TTL,
) -> None:
    key = _response_key(namespace, params or {})
    await _set_json_async(key, data, ttl)
    if ttl <= 0:
        _response_local_cache.pop(key, None)
    else:
        _set_local_response(key, data, ttl=ttl)


async def get_or_set_response(
    namespace: str,
    params: dict | None,
    producer: Callable[[], Awaitable[Any]],
    ttl: int = DEFAULT_RESPONSE_TTL,
    bypass: bool = False,
) -> Any:
    cache_params = params or {}
    key = _response_key(namespace, cache_params)
    lock_key = (asyncio.get_running_loop(), key)
    if bypass:
        lock_entry = _response_locks.get(lock_key)
        if lock_entry is None:
            lock_entry = _ResponseLockEntry(lock=asyncio.Lock())
            _response_locks[lock_key] = lock_entry

        task = lock_entry.bypass_task
        if task is None:
            task = asyncio.create_task(producer())
            lock_entry.bypass_task = task
        elif not task.done():
            _record_singleflight_wait()

        lock_entry.users += 1
        try:
            return await task
        finally:
            lock_entry.users -= 1
            if lock_entry.users == 0 and not lock_entry.lock.locked():
                _response_locks.pop(lock_key, None)

    cached = await get_response_async(namespace, cache_params)
    if cached is not None:
        return cached

    lock_entry = _response_locks.get(lock_key)
    if lock_entry is None:
        lock_entry = _ResponseLockEntry(lock=asyncio.Lock())
        _response_locks[lock_key] = lock_entry
    elif lock_entry.lock.locked():
        _record_singleflight_wait()

    lock_entry.users += 1
    try:
        async with lock_entry.lock:
            cached = await get_response_async(namespace, cache_params)
            if cached is not None:
                return cached
            data = await producer()
            await set_response_async(namespace, cache_params, data, ttl=ttl)
            return data
    finally:
        lock_entry.users -= 1
        if lock_entry.users == 0 and not lock_entry.lock.locked():
            _response_locks.pop(lock_key, None)


def _response_key(namespace: str, params: dict) -> str:
    stable = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    h = hashlib.sha256(stable.encode()).hexdigest()
    return f"response:{namespace}:{h}"


def _get_local_response(key: str) -> Any | None:
    entry = _response_local_cache.get(key)
    if entry is None:
        return None
    expires_at, data = entry
    if expires_at < time.monotonic():
        _response_local_cache.pop(key, None)
        return None
    return data


def _set_local_response(key: str, data: Any, ttl: int | float = _RESPONSE_LOCAL_TTL) -> None:
    ttl_seconds = max(0.0, min(float(ttl), _RESPONSE_LOCAL_TTL))
    if ttl_seconds <= 0:
        _response_local_cache.pop(key, None)
        return
    if len(_response_local_cache) >= _RESPONSE_LOCAL_MAX:
        _prune_local_response_cache()
    _response_local_cache[key] = (time.monotonic() + ttl_seconds, data)


def _prune_local_response_cache() -> None:
    now = time.monotonic()
    expired = [key for key, (expires_at, _data) in _response_local_cache.items() if expires_at < now]
    for key in expired:
        _response_local_cache.pop(key, None)
    while len(_response_local_cache) >= _RESPONSE_LOCAL_MAX:
        _response_local_cache.pop(next(iter(_response_local_cache)), None)


def should_bypass_response_cache(value: Any) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"0", "false", "f", "no", "n", "off"}


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
    local = _get_local_generation(namespace)
    if local is not None:
        return local
    data = _get_json(_generation_key(namespace))
    generation = int(data) if isinstance(data, int) else 0
    _set_local_generation(namespace, generation)
    return generation


async def get_data_generation_async(namespace: str) -> int:
    local = _get_local_generation(namespace)
    if local is not None:
        return local
    data = await _get_json_async(_generation_key(namespace))
    generation = int(data) if isinstance(data, int) else 0
    _set_local_generation(namespace, generation)
    return generation


def set_data_generation(namespace: str, generation: int, ttl: int = DEFAULT_ENUM_TTL) -> None:
    value = int(generation)
    _set_json(_generation_key(namespace), value, ttl)
    if ttl <= 0:
        _generation_cache.pop(namespace, None)
    else:
        _set_local_generation(namespace, value)


def _generation_key(namespace: str) -> str:
    return f"generation:{namespace}"


def _get_local_generation(namespace: str) -> int | None:
    entry = _generation_cache.get(namespace)
    if entry is None:
        return None
    expires_at, generation = entry
    if expires_at < time.monotonic():
        _generation_cache.pop(namespace, None)
        return None
    return generation


def _set_local_generation(namespace: str, generation: int) -> None:
    _generation_cache[namespace] = (time.monotonic() + _GENERATION_LOCAL_TTL, int(generation))


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
    _response_local_cache.clear()
    return int(get_backend().purge_response_cache())


def purge_enum_cache() -> int:
    """清除枚举原始缓存和对应的最终响应缓存，返回清除数量"""
    _response_local_cache.clear()
    return int(get_backend().purge_enum_cache())


def purge_all() -> int:
    """清除所有缓存"""
    _generation_cache.clear()
    _response_local_cache.clear()
    return int(get_backend().purge_all())
