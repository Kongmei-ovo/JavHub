from __future__ import annotations

import os
import sys
import unittest

from services import cache
from test_support.cache import (
    FakeRedisClient,
    FakeRedisMixin,
    RedisModulePatch,
    fake_redis_backend,
    make_fake_redis_module,
)


class FakeRedisSupportTest(FakeRedisMixin, unittest.TestCase):
    def test_fake_redis_mixin_exposes_legacy_client_alias_and_redis_backend(self):
        self.assertIs(self.fake_client, self.fake_redis_client)
        self.assertEqual(os.environ["JAVHUB_CACHE_BACKEND"], "redis")
        self.assertEqual(cache.get_backend_name(), "redis")

    def test_make_fake_redis_module_uses_the_given_client(self):
        client = FakeRedisClient()
        fake_redis = make_fake_redis_module(client)

        with RedisModulePatch(fake_redis):
            with self.subTest("from_url returns shared fake"):
                self.assertIs(fake_redis.Redis.from_url("redis://cache.example/0"), client)


def test_fake_redis_backend_configures_and_restores_cache_environment():
    original_backend = os.environ.get("JAVHUB_CACHE_BACKEND")
    original_url = os.environ.get("JAVHUB_REDIS_URL")
    original_prefix = os.environ.get("JAVHUB_REDIS_PREFIX")
    previous_redis_module = sys.modules.get("redis")

    with fake_redis_backend(prefix="context-prefix") as fake_client:
        assert os.environ["JAVHUB_CACHE_BACKEND"] == "redis"
        assert os.environ["JAVHUB_REDIS_URL"] == "redis://cache.example/0"
        assert os.environ["JAVHUB_REDIS_PREFIX"] == "context-prefix"

        cache.set_data_generation("javinfo", 9, ttl=60)

        assert cache.get_backend_name() == "redis"
        assert cache.get_data_generation("javinfo") == 9
        assert "context-prefix:generation:javinfo" in fake_client.values

    assert os.environ.get("JAVHUB_CACHE_BACKEND") == original_backend
    assert os.environ.get("JAVHUB_REDIS_URL") == original_url
    assert os.environ.get("JAVHUB_REDIS_PREFIX") == original_prefix
    assert sys.modules.get("redis") is previous_redis_module
