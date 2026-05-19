import tempfile
import time
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch

from routers import config as config_router
from services import cache


class CacheServiceTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

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


class CachePurgeRouteTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

    async def test_cache_purge_route_accepts_enum_scope(self):
        cache.set_response("categories", {}, [{"id": 1}], ttl=60)
        cache.set_enum_list("makers", [{"id": 2}])

        result = await config_router.purge_cache(scope="enum")

        self.assertEqual(result["scope"], "enum")
        self.assertEqual(result["purged"], 2)
        self.assertIsNone(cache.get_response("categories", {}))
        self.assertIsNone(cache.get_enum_list("makers"))


class ResponseCacheSingleflightTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

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

    async def test_producer_not_called_when_cached(self):
        cache.set_response("makers", {"page": 1}, {"data": [{"id": 1}]}, ttl=60)

        async def producer():
            raise AssertionError("producer should not be called on cache hit")

        result = await cache.get_or_set_response("makers", {"page": 1}, producer, ttl=60)

        self.assertEqual(result, {"data": [{"id": 1}]})


if __name__ == "__main__":
    unittest.main()
