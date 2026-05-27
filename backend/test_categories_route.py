import unittest
from unittest.mock import AsyncMock, Mock, patch

from routers import categories
from services import cache
from test_support.cache import FakeRedisMixin
from test_support.client import create_router_test_client
from test_support.translations import noop_entity_translator


class CategoryRouteTests(unittest.TestCase):
    def test_categories_router_no_longer_exposes_stats_endpoint(self):
        paths = {route.path for route in categories.router.routes}

        self.assertIn("/api/v1/categories", paths)
        self.assertNotIn("/api/v1/categories/stats", paths)


class CategoryRouteCacheTests(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_list_categories_caches_translated_response(self):
        mock_client = AsyncMock()
        mock_client.list_categories.return_value = [{"id": 1, "name_ja": "企画"}]
        mock_translator = noop_entity_translator()

        with patch("routers.categories.get_info_client", return_value=mock_client), \
             patch("routers.categories.get_translator_service", return_value=mock_translator):
            first = await categories.list_categories()
            second = await categories.list_categories()

        self.assertEqual(first, [{"id": 1, "name_ja": "企画"}])
        self.assertEqual(second, first)
        mock_client.list_categories.assert_awaited_once()
        mock_translator.translate_entities.assert_awaited_once()

    def test_cache_zero_bypasses_cached_categories_response(self):
        mock_client = AsyncMock()
        mock_client.list_categories.side_effect = [
            [{"id": 2, "name_ja": "response-old"}],
            [{"id": 3, "name_ja": "fresh"}],
        ]
        mock_translator = noop_entity_translator()

        with patch("routers.categories.get_info_client", return_value=mock_client), \
             patch("routers.categories.get_translator_service", return_value=mock_translator):
            http = create_router_test_client(categories.router)
            first = http.get("/api/v1/categories")
            cached = http.get("/api/v1/categories")
            fresh = http.get("/api/v1/categories?cache=0")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(first.json()[0]["name_ja"], "response-old")
        self.assertEqual(cached.json()[0]["name_ja"], "response-old")
        self.assertEqual(fresh.json()[0]["name_ja"], "fresh")
        self.assertEqual(mock_client.list_categories.await_count, 2)

    async def test_info_client_cache_bypass_ignores_enum_cache(self):
        from modules.info_client import InfoClient

        cache.set_enum_list("categories", [{"id": 1, "name_ja": "enum-old"}], ttl=60)
        client = InfoClient()

        with patch.object(client, "_get_all_pages", new_callable=AsyncMock) as get_all_pages:
            get_all_pages.return_value = [{"id": 2, "name_ja": "fresh"}]
            result = await client.list_categories(cache_bypass=True)

        self.assertEqual(result, [{"id": 2, "name_ja": "fresh"}])
        get_all_pages.assert_awaited_once_with("/api/v1/categories", cache_bypass=True)

    async def test_info_client_all_pages_cache_bypass_forwards_upstream_cache_zero(self):
        from modules.info_client import InfoClient

        client = InfoClient()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": [{"id": 1}], "total_pages": 1}
        http = AsyncMock()
        http.get.return_value = response

        with patch.object(client, "_get_client", AsyncMock(return_value=http)):
            result = await client._get_all_pages("/api/v1/categories", cache_bypass=True)

        self.assertEqual(result, [{"id": 1}])
        http.get.assert_awaited_once()
        self.assertEqual(http.get.await_args.kwargs["params"]["cache"], "0")


if __name__ == "__main__":
    unittest.main()
