import time
import asyncio
from typing import Dict, Optional, Any
from threading import Lock

class CacheItem:
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class MemoryCache:
    """简单的内存缓存"""

    def __init__(self):
        self._cache: Dict[str, CacheItem] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            if item.is_expired():
                del self._cache[key]
                return None
            return item.value

    def set(self, key: str, value: Any, ttl: int = 300):
        with self._lock:
            self._cache[key] = CacheItem(value, ttl)

    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self):
        """清理过期缓存"""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]

# 全局缓存实例
cache = MemoryCache()

# 缓存键名常量
CACHE_KEYS = {
    'search': 'search:{}',  # search:{keyword}
    'actor_movies': 'actor:{}',  # actor:{actor_name}
    'emby_check': 'emby:{}',  # emby:{code}
}
