from __future__ import annotations

import inspect
import threading
import unittest
from unittest.mock import Mock, patch

from test_support.cache import FakeRedisMixin


class SyncRouteDispatchTest(unittest.TestCase):
    def test_db_bound_read_routes_are_sync_for_threadpool_dispatch(self):
        from routers import downloads, favorites, video_variant_index

        handlers = [
            downloads.list_candidate_runs,
            downloads.get_candidate,
            favorites.get_collections,
            video_variant_index.list_variant_index_jobs,
            video_variant_index.get_variant_index_job,
        ]

        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                self.assertFalse(inspect.iscoroutinefunction(handler))

    def test_cached_hot_read_routes_are_async_to_avoid_threadpool_queueing(self):
        from routers import downloads, favorites, logs

        handlers = [
            downloads.list_downloads,
            downloads.list_candidates,
            downloads.candidate_summary,
            favorites.get_favorites,
            logs.get_logs,
        ]

        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                self.assertTrue(inspect.iscoroutinefunction(handler))


class AsyncRouteBlockingTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    async def test_favorite_videos_loads_favorite_rows_off_event_loop(self):
        from routers import favorites

        release_db = threading.Event()
        observation: dict[str, bool] = {}

        def list_favorites(_entity_type: str):
            release_db.wait(timeout=1)
            return []

        async def marker():
            observation["ran_while_db_waited"] = not release_db.is_set()

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch.object(favorites.favorite, "list_favorites", Mock(side_effect=list_favorites)):
                result, _ = await __import__("asyncio").gather(
                    favorites.get_favorite_videos(),
                    marker(),
                )
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(result, [])
        self.assertTrue(observation["ran_while_db_waited"])

    async def test_subscriptions_list_builds_payload_off_event_loop(self):
        from routers import subscriptions

        release_db = threading.Event()
        observation: dict[str, bool] = {}

        def get_subscriptions():
            release_db.wait(timeout=1)
            return []

        async def marker():
            observation["ran_while_db_waited"] = not release_db.is_set()

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch.object(subscriptions, "get_subscriptions", Mock(side_effect=get_subscriptions)), \
                patch.object(subscriptions, "download_candidate_counts_by_actress", Mock(return_value={})):
                result, _ = await __import__("asyncio").gather(
                    subscriptions.list_subscriptions(),
                    marker(),
                )
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(result["data"], [])
        self.assertTrue(observation["ran_while_db_waited"])

    async def test_new_movies_builds_payload_off_event_loop(self):
        from routers import subscriptions

        release_db = threading.Event()
        observation: dict[str, bool] = {}

        def get_subscriptions():
            release_db.wait(timeout=1)
            return []

        async def marker():
            observation["ran_while_db_waited"] = not release_db.is_set()

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch.object(subscriptions, "get_subscriptions", Mock(side_effect=get_subscriptions)), \
                patch.object(subscriptions, "list_download_candidates_by_actress_ids", Mock(return_value={})):
                result, _ = await __import__("asyncio").gather(
                    subscriptions.get_new_movies(),
                    marker(),
                )
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(result["data"], {})
        self.assertTrue(observation["ran_while_db_waited"])

    async def test_translation_items_loads_workbench_rows_off_event_loop(self):
        from routers import translation

        release_db = threading.Event()
        observation: dict[str, bool] = {}

        def list_items(**_kwargs):
            release_db.wait(timeout=1)
            return {"data": [], "total": 0, "page": 1, "page_size": 50, "total_pages": 1}

        async def marker():
            observation["ran_while_db_waited"] = not release_db.is_set()

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch.object(translation, "list_translation_workbench_items", Mock(side_effect=list_items)), \
                patch.object(translation, "translation_workbench_stats", Mock(return_value={})):
                result, _ = await __import__("asyncio").gather(
                    translation.list_translation_items(page=1, page_size=50),
                    marker(),
                )
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(result["data"], [])
        self.assertTrue(observation["ran_while_db_waited"])

    async def test_translation_stats_loads_local_counts_off_event_loop(self):
        from routers import translation

        release_db = threading.Event()
        observation: dict[str, bool] = {}

        def get_translation_count(_mapping_type: str):
            release_db.wait(timeout=1)
            return 0

        class Client:
            async def get_total_count(self, _path: str, cache_bypass: bool = False) -> int:
                return 0

        async def marker():
            await __import__("asyncio").sleep(0.01)
            observation["ran_while_db_waited"] = not release_db.is_set()

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch.object(translation, "get_translation_count", Mock(side_effect=get_translation_count)), \
                patch.object(translation, "get_translation_coverage_counts", Mock(return_value={})), \
                patch.object(translation, "get_translation_cache_count", Mock(return_value=0)), \
                patch.object(translation, "translation_workbench_stats", Mock(return_value={})), \
                patch.object(translation, "get_info_client", Mock(return_value=Client())):
                result, _ = await __import__("asyncio").gather(
                    translation.all_stats(cache_control="0"),
                    marker(),
                )
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(result["ai_cache"], 0)
        self.assertTrue(observation["ran_while_db_waited"])


if __name__ == "__main__":
    unittest.main()
