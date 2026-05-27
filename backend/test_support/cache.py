from __future__ import annotations

import fnmatch
import os
import sys
import time
import types
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch


class RedisModulePatch:
    def __init__(self, fake_redis):
        self.fake_redis = fake_redis
        self._sentinel = object()
        self._previous = self._sentinel

    def start(self):
        self._previous = sys.modules.get("redis", self._sentinel)
        sys.modules["redis"] = self.fake_redis
        return self.fake_redis

    def stop(self):
        if self._previous is self._sentinel:
            sys.modules.pop("redis", None)
        else:
            sys.modules["redis"] = self._previous

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False


class FakeRedisClient:
    def __init__(self):
        self.values = {}
        self.expiry = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        if ex is not None:
            self.expiry[key] = time.time() + ex

    def scan_iter(self, match=None, count=None):
        return [key for key in self.values if match is None or fnmatch.fnmatch(key, match)]

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.values:
                deleted += 1
                self.values.pop(key, None)
                self.expiry.pop(key, None)
        return deleted

    def ttl(self, key):
        expires_at = self.expiry.get(key)
        if expires_at is None:
            return -1
        return int(expires_at - time.time())


def make_fake_redis_module(client):
    return types.SimpleNamespace(
        Redis=types.SimpleNamespace(from_url=lambda url, decode_responses=True: client)
    )


@contextmanager
def fake_redis_backend(
    *,
    prefix: str,
    client: FakeRedisClient | None = None,
    url: str = "redis://cache.example/0",
    backend: str | None = "redis",
) -> Iterator[FakeRedisClient]:
    fake_client = client or FakeRedisClient()
    fake_redis = make_fake_redis_module(fake_client)
    env = {
        "JAVHUB_REDIS_URL": url,
        "JAVHUB_REDIS_PREFIX": prefix,
    }
    if backend is not None:
        env["JAVHUB_CACHE_BACKEND"] = backend

    with patch.dict(os.environ, env, clear=False), RedisModulePatch(fake_redis):
        if backend is None:
            os.environ.pop("JAVHUB_CACHE_BACKEND", None)

        from services import cache

        cache.reset_backend()
        cache.reset_metrics()
        try:
            yield fake_client
        finally:
            cache.reset_backend()


class FakeRedisMixin:
    def setUp(self):
        super().setUp()
        self.fake_redis_client = FakeRedisClient()
        self.fake_client = self.fake_redis_client
        fake_redis = make_fake_redis_module(self.fake_redis_client)
        self.redis_env_patch = patch.dict(os.environ, {
            "JAVHUB_CACHE_BACKEND": "redis",
            "JAVHUB_REDIS_URL": "redis://cache.example/0",
            "JAVHUB_REDIS_PREFIX": f"test-prefix-{id(self)}",
        }, clear=False)
        self.redis_module_patch = RedisModulePatch(fake_redis)
        self.redis_env_patch.start()
        self.redis_module_patch.start()

        from services import cache

        cache.reset_backend()
        cache.reset_metrics()

    def tearDown(self):
        from services import cache

        cache.reset_backend()
        self.redis_module_patch.stop()
        self.redis_env_patch.stop()
        super().tearDown()
