from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from routers import actresses


class ActressesRouterTest(unittest.IsolatedAsyncioTestCase):
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
