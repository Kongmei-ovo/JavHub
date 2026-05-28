from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from routers import actresses
from test_support.cache import FakeRedisMixin
from test_support.translations import noop_entity_translator


class ActressesRouterTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_list_actresses_passes_valid_avatar_filter(self):
        mock_client = AsyncMock()
        mock_client.list_actresses.return_value = {"data": [], "total_count": 0}

        with patch("routers.actresses.get_info_client", return_value=mock_client):
            result = await actresses.list_actresses(page=2, page_size=36, has_valid_avatar="1")

        self.assertEqual(result, {"data": [], "total_count": 0})
        mock_client.list_actresses.assert_awaited_once_with(
            q=None,
            page=2,
            page_size=36,
            has_valid_avatar="1",
        )

    async def test_list_actresses_caches_by_query_params(self):
        mock_client = AsyncMock()
        mock_client.list_actresses.return_value = {
            "data": [{"id": 1, "name_kanji": "三上"}],
            "page": 1,
            "page_size": 20,
        }
        mock_translator = noop_entity_translator()

        with patch("routers.actresses.get_info_client", return_value=mock_client), \
             patch("routers.actresses.get_translator_service", return_value=mock_translator):
            first = await actresses.list_actresses(page=1, page_size=20, has_valid_avatar=None)
            second = await actresses.list_actresses(page=1, page_size=20, has_valid_avatar=None)
            third = await actresses.list_actresses(page=2, page_size=20, has_valid_avatar=None)

        self.assertEqual(second, first)
        self.assertEqual(third, first)
        self.assertEqual(mock_client.list_actresses.await_count, 2)
        self.assertEqual(mock_translator.translate_entities.await_count, 2)

    async def test_get_actress_uses_movie_count_from_detail_response(self):
        mock_client = AsyncMock()
        mock_client.get_actress.return_value = {"id": 1, "name_kanji": "三上", "movie_count": 99}
        mock_translator = noop_entity_translator()

        with patch("routers.actresses.get_info_client", return_value=mock_client), \
             patch("routers.actresses.get_translator_service", return_value=mock_translator):
            result = await actresses.get_actress(1)

        self.assertEqual(result["movie_count"], 99)
        mock_client.get_actress_videos.assert_not_awaited()
