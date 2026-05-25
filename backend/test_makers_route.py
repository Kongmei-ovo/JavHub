from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import makers
from test_support.cache import FakeRedisMixin


class MakersRouterTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_list_makers_uses_paginated_javinfo_endpoint(self):
        mock_client = AsyncMock()
        mock_client.list_makers_page.return_value = {
            "data": [{"id": 1, "name_ja": "企画"}],
            "page": 2,
            "page_size": 10,
            "total_count": 30,
            "total_pages": 3,
        }
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.makers.get_info_client", return_value=mock_client), \
             patch("routers.makers.get_translator_service", return_value=mock_translator):
            result = await makers.list_makers(page=2, page_size=10, q="企画")

        self.assertEqual(result["data"], [{"id": 1, "name_ja": "企画"}])
        mock_client.list_makers_page.assert_awaited_once_with(q="企画", page=2, page_size=10, include_total=False)
        mock_client.list_makers.assert_not_called()
        mock_translator.translate_entities.assert_awaited_once_with(
            result["data"],
            entity_type="maker",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )

    async def test_list_makers_keeps_local_pagination_for_legacy_list_response(self):
        mock_client = AsyncMock()
        mock_client.list_makers_page.return_value = [
            {"id": 1, "name_ja": "一"},
            {"id": 2, "name_ja": "二"},
            {"id": 3, "name_ja": "三"},
        ]
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.makers.get_info_client", return_value=mock_client), \
             patch("routers.makers.get_translator_service", return_value=mock_translator):
            result = await makers.list_makers(page=2, page_size=2, q=None)

        self.assertEqual(result["data"], [{"id": 3, "name_ja": "三"}])
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["total_pages"], 2)
        mock_client.list_makers_page.assert_awaited_once_with(q=None, page=2, page_size=2, include_total=False)

    async def test_list_makers_cache_key_includes_page_params(self):
        mock_client = AsyncMock()
        mock_client.list_makers_page.side_effect = [
            {
                "data": [{"id": 1, "name_ja": "一"}],
                "page": 1,
                "page_size": 1,
                "total_count": 2,
                "total_pages": 2,
            },
            {
                "data": [{"id": 2, "name_ja": "二"}],
                "page": 2,
                "page_size": 1,
                "total_count": 2,
                "total_pages": 2,
            },
        ]
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.makers.get_info_client", return_value=mock_client), \
             patch("routers.makers.get_translator_service", return_value=mock_translator):
            first = await makers.list_makers(page=1, page_size=1, q=None)
            second = await makers.list_makers(page=2, page_size=1, q=None)
            first_cached = await makers.list_makers(page=1, page_size=1, q=None)

        self.assertEqual(first["data"], [{"id": 1, "name_ja": "一"}])
        self.assertEqual(second["data"], [{"id": 2, "name_ja": "二"}])
        self.assertEqual(first_cached, first)
        self.assertEqual(mock_client.list_makers_page.await_count, 2)

    def test_cache_zero_bypasses_cached_makers_response(self):
        app = FastAPI()
        app.include_router(makers.router)
        mock_client = AsyncMock()
        mock_client.list_makers_page.side_effect = [
            {"data": [{"id": 1, "name_ja": "old"}], "page": 1, "page_size": 20},
            {"data": [{"id": 2, "name_ja": "fresh"}], "page": 1, "page_size": 20},
        ]
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.makers.get_info_client", return_value=mock_client), \
             patch("routers.makers.get_translator_service", return_value=mock_translator):
            http = TestClient(app)
            first = http.get("/api/v1/makers")
            cached = http.get("/api/v1/makers")
            fresh = http.get("/api/v1/makers?cache=0")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(first.json()["data"][0]["name_ja"], "old")
        self.assertEqual(cached.json()["data"][0]["name_ja"], "old")
        self.assertEqual(fresh.json()["data"][0]["name_ja"], "fresh")
        self.assertEqual(mock_client.list_makers_page.await_count, 2)
        self.assertTrue(
            any(call.kwargs.get("cache_bypass") is True for call in mock_client.list_makers_page.await_args_list)
        )


if __name__ == "__main__":
    unittest.main()
