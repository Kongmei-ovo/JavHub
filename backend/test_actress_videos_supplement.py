from __future__ import annotations
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import actresses


class ActressVideosSupplementTest(unittest.IsolatedAsyncioTestCase):
    async def test_passes_include_supplement_to_client(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {"data": [{"content_id": "abc"}], "total_count": 1}

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


class ActressBatchVideosRouterTest(unittest.TestCase):
    def test_batch_videos_route_forwards_ids_to_javinfoapi(self):
        app = FastAPI()
        app.include_router(actresses.router)
        mock_client = AsyncMock()
        mock_client.batch_get_actress_videos.return_value = {
            "26225": {
                "total_count": 1,
                "videos": [{"content_id": "abc", "title_ja": "Title"}],
            }
        }
        translator = AsyncMock()
        translator.translate_video.side_effect = lambda _content_id, data, **_kwargs: data

        with (
            patch("routers.actresses.get_info_client", return_value=mock_client),
            patch("routers.actresses.get_translator_service", return_value=translator),
        ):
            response = TestClient(app).post(
                "/api/v1/actresses/batch_videos",
                json={"ids": [26225], "page": 2, "page_size": 3},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["26225"]["total_count"], 1)
        mock_client.batch_get_actress_videos.assert_awaited_once_with([26225], page=2, page_size=3)
        translator.translate_video.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
