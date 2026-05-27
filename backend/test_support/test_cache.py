from __future__ import annotations

import os
import unittest

from services import cache
from test_support.cache import (
    FakeRedisClient,
    FakeRedisMixin,
    RedisModulePatch,
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
