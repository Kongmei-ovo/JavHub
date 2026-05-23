from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.cache import FakeRedisMixin


class SeriesRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_series_route_uses_paged_client_call(self):
        from routers.series import list_series

        client = AsyncMock()
        client.list_series_page.return_value = {
            "data": [{"id": 1, "name_ja": "シリーズ"}],
            "page": 3,
            "page_size": 24,
            "total_count": 100,
            "total_pages": 5,
        }
        translator = AsyncMock()

        with patch("routers.series.get_info_client", return_value=client), \
             patch("routers.series.get_translator_service", return_value=translator):
            result = await list_series(page=3, page_size=24, q=None)

        client.list_series_page.assert_awaited_once_with(q=None, page=3, page_size=24, include_total=False)
        client.list_series.assert_not_called()
        translator.translate_entities.assert_awaited_once_with(
            result["data"],
            entity_type="series",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )
        self.assertEqual(result["total_count"], 100)


if __name__ == "__main__":
    unittest.main()
