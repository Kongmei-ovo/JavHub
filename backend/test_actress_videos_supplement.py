from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import actresses
from services import cache


class ActressVideosSupplementTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

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

    async def test_actress_videos_caches_translated_response_by_filters(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.side_effect = [
            {"data": [{"content_id": "abc", "title_ja": "原文"}], "total_count": 1},
            {"data": [{"content_id": "abc", "title_ja": "別版"}], "total_count": 1},
        ]
        translator = AsyncMock()
        translator.translate_videos.side_effect = [
            [{"content_id": "abc", "title_ja": "译文"}],
            [{"content_id": "abc", "title_ja": "別版译文"}],
        ]

        with (
            patch("routers.actresses.get_info_client", return_value=mock_client),
            patch("routers.actresses.get_translator_service", return_value=translator),
        ):
            first = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                service_code="digital",
                year=2024,
                sort_by="release_date:desc",
            )
            second = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                service_code="digital",
                year=2024,
                sort_by="release_date:desc",
            )
            other_year = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                service_code="digital",
                year=2023,
                sort_by="release_date:desc",
            )

        self.assertEqual(second, first)
        self.assertEqual(other_year["data"][0]["title_ja"], "別版译文")
        self.assertEqual(mock_client.get_actress_videos.await_count, 2)
        self.assertEqual(translator.translate_videos.await_count, 2)


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
        translator.translate_videos.side_effect = lambda items, **_kwargs: items

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
        translator.translate_videos.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
