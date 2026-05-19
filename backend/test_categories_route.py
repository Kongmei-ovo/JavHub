import unittest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from routers import categories
from services import cache


class CategoryRouteTests(unittest.TestCase):
    def test_categories_router_no_longer_exposes_stats_endpoint(self):
        paths = {route.path for route in categories.router.routes}

        self.assertIn("/api/v1/categories", paths)
        self.assertNotIn("/api/v1/categories/stats", paths)


class CategoryRouteCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

    async def test_list_categories_caches_translated_response(self):
        mock_client = AsyncMock()
        mock_client.list_categories.return_value = [{"id": 1, "name_ja": "企画"}]
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.categories.get_info_client", return_value=mock_client), \
             patch("routers.categories.get_translator_service", return_value=mock_translator):
            first = await categories.list_categories()
            second = await categories.list_categories()

        self.assertEqual(first, [{"id": 1, "name_ja": "企画"}])
        self.assertEqual(second, first)
        mock_client.list_categories.assert_awaited_once()
        mock_translator.translate_entities.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
