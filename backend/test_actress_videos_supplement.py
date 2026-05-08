from __future__ import annotations
import unittest
from unittest.mock import AsyncMock, patch

from routers import actresses


class ActressVideosSupplementTest(unittest.IsolatedAsyncioTestCase):
    async def test_passes_include_supplement_to_client(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {"data": [], "total_count": 0}

        with patch("routers.actresses.get_info_client", return_value=mock_client):
            await actresses.get_actress_videos(
                actress_id=123, page=1, page_size=20,
                include_supplement="1", service_code="digital", year=2024,
                sort_by="release_date:desc",
            )

        mock_client.get_actress_videos.assert_awaited_once_with(
            123, page=1, page_size=20,
            include_supplement="1", service_code="digital", year=2024,
            sort_by="release_date:desc",
        )

    async def test_no_extra_params_when_not_provided(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {"data": [], "total_count": 0}

        with patch("routers.actresses.get_info_client", return_value=mock_client):
            await actresses.get_actress_videos(actress_id=123, page=1, page_size=20)

        mock_client.get_actress_videos.assert_awaited_once_with(
            123, page=1, page_size=20,
            include_supplement=None, service_code=None, year=None, sort_by=None,
        )


if __name__ == "__main__":
    unittest.main()
