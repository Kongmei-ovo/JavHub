import asyncio
import unittest
from unittest.mock import patch

from routers import categories


class CategoryStatsTests(unittest.IsolatedAsyncioTestCase):
    async def test_category_stats_limits_upstream_search_concurrency(self):
        active = 0
        max_active = 0

        class ClientStub:
            async def list_categories(self):
                return [{"id": i, "name": f"cat-{i}"} for i in range(20)]

            async def search_videos(self, category_id, page, page_size):
                nonlocal active, max_active
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.001)
                active -= 1
                return {"total_count": category_id}

        with patch("routers.categories.cache.get_category_stats", return_value=None), \
             patch("routers.categories.cache.set_category_stats") as set_cache, \
             patch("routers.categories.get_info_client", return_value=ClientStub()):
            result = await categories.category_stats()

        self.assertEqual(len(result), 20)
        self.assertLessEqual(max_active, categories.CATEGORY_STATS_CONCURRENCY)
        set_cache.assert_called_once()

    async def test_category_stats_uses_total_count_field(self):
        class ClientStub:
            async def list_categories(self):
                return [{"id": 7, "name": "cat"}]

            async def search_videos(self, category_id, page, page_size):
                return {"total_count": 123}

        with patch("routers.categories.cache.get_category_stats", return_value=None), \
             patch("routers.categories.cache.set_category_stats"), \
             patch("routers.categories.get_info_client", return_value=ClientStub()):
            result = await categories.category_stats()

        self.assertEqual(result[0]["video_count"], 123)


if __name__ == "__main__":
    unittest.main()
