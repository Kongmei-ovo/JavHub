import time
import unittest
import asyncio
import os
from unittest.mock import patch

from routers import config as config_router
from services import cache
from test_support.cache import (
    FakeRedisMixin,
    fake_redis_backend,
)


class CacheServiceTest(FakeRedisMixin, unittest.TestCase):

    def test_video_cache_round_trips_json_without_pickle(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"}, ttl=60)

        self.assertEqual(cache.get_video("abc-123"), {"content_id": "ABC-123"})

    def test_expired_items_are_removed(self):
        cache.set_search({"q": "abc"}, 1, {"data": []}, ttl=0)
        time.sleep(0.01)

        self.assertIsNone(cache.get_search({"q": "abc"}, 1))

    def test_purge_video_cache_removes_video_and_search_only(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"})
        cache.set_search({"q": "abc"}, 1, {"data": []})
        cache.set_enum_list("makers", [{"id": 1}])

        self.assertEqual(cache.purge_video_cache(), 2)
        self.assertIsNone(cache.get_video("abc-123"))
        self.assertIsNone(cache.get_search({"q": "abc"}, 1))
        self.assertEqual(cache.get_enum_list("makers"), [{"id": 1}])

    def test_response_cache_round_trips_by_namespace_and_params(self):
        cache.set_response(
            "actresses",
            {"page_size": 20, "page": 1},
            {"data": [{"id": 1}], "page": 1},
            ttl=60,
        )

        self.assertEqual(
            cache.get_response("actresses", {"page": 1, "page_size": 20}),
            {"data": [{"id": 1}], "page": 1},
        )
        self.assertIsNone(cache.get_response("actresses", {"page": 2, "page_size": 20}))

    def test_purge_response_cache_removes_only_response_entries(self):
        cache.set_response("categories", {}, [{"id": 1}], ttl=60)
        cache.set_enum_list("makers", [{"id": 2}])
        cache.set_video("abc-123", {"content_id": "ABC-123"})

        self.assertEqual(cache.purge_response_cache(), 1)
        self.assertIsNone(cache.get_response("categories", {}))
        self.assertEqual(cache.get_enum_list("makers"), [{"id": 2}])
        self.assertEqual(cache.get_video("abc-123"), {"content_id": "ABC-123"})

    def test_purge_enum_cache_removes_enum_and_response_entries(self):
        cache.set_response("categories", {}, [{"id": 1}], ttl=60)
        cache.set_enum_list("makers", [{"id": 2}])
        cache.set_video("abc-123", {"content_id": "ABC-123"})

        self.assertEqual(cache.purge_enum_cache(), 2)
        self.assertIsNone(cache.get_response("categories", {}))
        self.assertIsNone(cache.get_enum_list("makers"))
        self.assertEqual(cache.get_video("abc-123"), {"content_id": "ABC-123"})

    def test_cache_stats_counts_entries_by_kind_and_response_namespace(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"})
        cache.set_search({"q": "abc"}, 1, {"data": []})
        cache.set_enum_list("makers", [{"id": 2}])
        cache.set_response("videos", {"page": 1}, {"data": []})
        cache.set_response("videos", {"page": 2}, {"data": []})
        cache.set_response("actress_videos", {"actress_id": 1}, {"data": []})
        cache.set_response("expired", {}, {"data": []}, ttl=0)
        time.sleep(0.01)

        stats = cache.get_stats()

        self.assertEqual(stats["total_entries"], 6)
        self.assertEqual(stats["expired_entries"], 0)
        self.assertEqual(stats["active_entries"], 6)
        self.assertEqual(stats["by_kind"]["video"], 1)
        self.assertEqual(stats["by_kind"]["search"], 1)
        self.assertEqual(stats["by_kind"]["enum"], 1)
        self.assertEqual(stats["by_kind"]["response"], 3)
        self.assertEqual(stats["response_namespaces"]["videos"], 2)
        self.assertEqual(stats["response_namespaces"]["actress_videos"], 1)

    def test_cache_stats_include_hit_miss_metrics(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"})
        cache.set_search({"q": "abc"}, 1, {"data": []})
        cache.set_enum_list("makers", [{"id": 1}])
        cache.set_response("videos", {"page": 1}, {"data": []})

        cache.get_video("abc-123")
        cache.get_video("missing")
        cache.get_search({"q": "abc"}, 1)
        cache.get_search({"q": "missing"}, 1)
        cache.get_enum_list("makers")
        cache.get_enum_list("labels")
        cache.get_response("videos", {"page": 1})
        cache.get_response("videos", {"page": 2})

        metrics = cache.get_stats()["metrics"]

        self.assertEqual(metrics["video"], {"hits": 1, "misses": 1})
        self.assertEqual(metrics["search"], {"hits": 1, "misses": 1})
        self.assertEqual(metrics["enum"], {"hits": 1, "misses": 1})
        self.assertEqual(metrics["response"], {"hits": 1, "misses": 1})
        self.assertEqual(metrics["response_namespaces"]["videos"], {"hits": 1, "misses": 1})

    def test_data_generation_round_trips_by_namespace(self):
        self.assertEqual(cache.get_data_generation("javinfo"), 0)

        cache.set_data_generation("javinfo", 42)

        self.assertEqual(cache.get_data_generation("javinfo"), 42)
        self.assertEqual(cache.get_data_generation("other"), 0)

    def test_data_generation_uses_current_cache_backend(self):
        with fake_redis_backend(prefix="generation-prefix") as fake_client:
            cache.set_data_generation("javinfo", 7, ttl=60)

            self.assertEqual(cache.get_data_generation("javinfo"), 7)
            self.assertIn("generation-prefix:generation:javinfo", fake_client.values)

    def test_default_cache_backend_is_redis(self):
        with fake_redis_backend(prefix="default-prefix", backend=None):
            self.assertEqual(cache.get_backend_name(), "redis")
            self.assertIsInstance(cache.get_backend(), cache.RedisCacheBackend)

    def test_redis_backend_round_trips_without_changing_cache_api(self):
        with fake_redis_backend(prefix="test-prefix"):
            cache.set_response("videos", {"page": 1}, {"data": [{"id": 1}]}, ttl=60)

            self.assertEqual(cache.get_backend_name(), "redis")
            self.assertEqual(cache.get_response("videos", {"page": 1}), {"data": [{"id": 1}]})
            self.assertEqual(cache.get_stats()["response_namespaces"]["videos"], 1)
            self.assertEqual(cache.purge_response_cache(), 1)
            self.assertIsNone(cache.get_response("videos", {"page": 1}))

    def test_redis_backend_purge_only_deletes_current_prefix(self):
        with fake_redis_backend(prefix="current-prefix") as fake_client:
            backend = cache.get_backend()

            backend.set_json("video:abc-123", {"content_id": "ABC-123"}, ttl=60)
            backend.set_json("search:abc:1", {"data": []}, ttl=60)
            fake_client.set("other-prefix:video:abc-123", '{"content_id":"OTHER"}', ex=60)
            fake_client.set("current-prefix-extra:video:abc-123", '{"content_id":"EXTRA"}', ex=60)

            self.assertEqual(cache.purge_video_cache(), 2)
            self.assertNotIn("current-prefix:video:abc-123", fake_client.values)
            self.assertNotIn("current-prefix:search:abc:1", fake_client.values)
            self.assertEqual(fake_client.values["other-prefix:video:abc-123"], '{"content_id":"OTHER"}')
            self.assertEqual(fake_client.values["current-prefix-extra:video:abc-123"], '{"content_id":"EXTRA"}')

    def test_redis_backend_requires_url(self):
        with patch.dict(os.environ, {
            "JAVHUB_CACHE_BACKEND": "redis",
            "JAVHUB_REDIS_URL": "",
        }, clear=False):
            cache.reset_backend()

            with self.assertRaisesRegex(RuntimeError, "JAVHUB_REDIS_URL"):
                cache.get_backend()

        cache.reset_backend()


class CachePurgeRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    async def test_cache_purge_route_accepts_enum_scope(self):
        cache.set_response("categories", {}, [{"id": 1}], ttl=60)
        cache.set_enum_list("makers", [{"id": 2}])

        result = await config_router.purge_cache(scope="enum")

        self.assertEqual(result["scope"], "enum")
        self.assertEqual(result["purged"], 2)
        self.assertIsNone(cache.get_response("categories", {}))
        self.assertIsNone(cache.get_enum_list("makers"))

    async def test_cache_purge_route_rejects_unknown_scope(self):
        with self.assertRaises(Exception) as ctx:
            await config_router.purge_cache(scope="typo")

        self.assertEqual(getattr(ctx.exception, "status_code", None), 400)
        self.assertEqual(getattr(ctx.exception, "detail", None), "Unsupported cache purge scope")

    async def test_cache_stats_route_returns_service_stats(self):
        cache.set_response("videos", {"page": 1}, {"data": []}, ttl=60)

        result = await config_router.get_cache_stats()

        self.assertEqual(result["total_entries"], 1)
        self.assertEqual(result["response_namespaces"]["videos"], 1)


class ResponseCacheSingleflightTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_misses_share_one_producer_call(self):
        calls = 0

        async def producer():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"data": [{"id": 1}]}

        results = await asyncio.gather(
            *(
                cache.get_or_set_response("makers", {"page": 1}, producer, ttl=60)
                for _ in range(5)
            )
        )

        self.assertEqual(results, [{"data": [{"id": 1}]}] * 5)
        self.assertEqual(calls, 1)
        self.assertGreaterEqual(cache.get_stats()["metrics"]["singleflight_waits"], 4)
        self.assertEqual(cache.get_stats()["singleflight_locks"], 0)

    async def test_producer_not_called_when_cached(self):
        cache.set_response("makers", {"page": 1}, {"data": [{"id": 1}]}, ttl=60)

        async def producer():
            raise AssertionError("producer should not be called on cache hit")

        result = await cache.get_or_set_response("makers", {"page": 1}, producer, ttl=60)

        self.assertEqual(result, {"data": [{"id": 1}]})

    async def test_bypass_ignores_cached_response_and_does_not_store_result(self):
        cache.set_response("makers", {"page": 1}, {"data": [{"id": 1}]}, ttl=60)

        async def producer():
            return {"data": [{"id": 2}]}

        result = await cache.get_or_set_response("makers", {"page": 1}, producer, ttl=60, bypass=True)

        self.assertEqual(result, {"data": [{"id": 2}]})
        self.assertEqual(cache.get_response("makers", {"page": 1}), {"data": [{"id": 1}]})

    async def test_high_cardinality_response_misses_do_not_retain_idle_locks(self):
        calls = 0

        async def producer():
            nonlocal calls
            calls += 1
            return {"data": [{"id": calls}]}

        for page in range(50):
            result = await cache.get_or_set_response("makers", {"page": page}, producer, ttl=60)
            self.assertEqual(result, {"data": [{"id": page + 1}]})

        self.assertEqual(calls, 50)
        self.assertEqual(cache.get_stats()["singleflight_locks"], 0)


if __name__ == "__main__":
    unittest.main()
