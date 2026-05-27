from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from routers import labels
from test_support.builders import page_response
from test_support.cache import FakeRedisMixin


class LabelsRouterTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_list_labels_uses_paginated_javinfo_endpoint(self):
        mock_client = AsyncMock()
        mock_client.list_labels_page.return_value = page_response(
            [{"id": 1, "name_ja": "企画"}],
            page=2,
            page_size=10,
            total_count=30,
            total_pages=3,
        )
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.labels.get_info_client", return_value=mock_client), \
             patch("routers.labels.get_translator_service", return_value=mock_translator):
            result = await labels.list_labels(page=2, page_size=10, q="企画")

        self.assertEqual(result["data"], [{"id": 1, "name_ja": "企画"}])
        mock_client.list_labels_page.assert_awaited_once_with(q="企画", page=2, page_size=10, include_total=False)
        mock_client.list_labels.assert_not_called()
        mock_translator.translate_entities.assert_awaited_once_with(
            result["data"],
            entity_type="label",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )

    async def test_list_labels_keeps_local_pagination_for_legacy_list_response(self):
        mock_client = AsyncMock()
        mock_client.list_labels_page.return_value = [
            {"id": 1, "name_ja": "一"},
            {"id": 2, "name_ja": "二"},
            {"id": 3, "name_ja": "三"},
        ]
        mock_translator = AsyncMock()
        mock_translator.translate_entities.return_value = None

        with patch("routers.labels.get_info_client", return_value=mock_client), \
             patch("routers.labels.get_translator_service", return_value=mock_translator):
            result = await labels.list_labels(page=2, page_size=2, q=None)

        self.assertEqual(result["data"], [{"id": 3, "name_ja": "三"}])
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["total_pages"], 2)
        mock_client.list_labels_page.assert_awaited_once_with(q=None, page=2, page_size=2, include_total=False)


if __name__ == "__main__":
    unittest.main()
