from __future__ import annotations
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI

from routers import actresses
from test_support.cache import FakeRedisMixin
from test_support.client import create_test_client
from test_support.postgres import TempPostgresMixin


class ActressVideosSupplementTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):

    async def test_passes_include_supplement_to_client(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {"data": [{"content_id": "abc"}], "total_count": 1}

        with patch("routers.actresses.get_info_client", return_value=mock_client):
            result = await actresses.get_actress_videos(
                actress_id=123, page=1, page_size=20,
            include_supplement="1", service_code="digital", year=2024,
            sort_by="release_date:desc",
            variant_mode="grouped",
            variant_scope="page",
            include_variant_explanations=True,
        )

        mock_client.get_actress_videos.assert_awaited_once_with(
            123, page=1, page_size=20,
            include_supplement="1", service_code="digital", year=2024,
            sort_by="release_date:desc", include_total=None,
        )
        self.assertEqual(result["data"][0]["variant_group_count"], 1)

    async def test_no_extra_params_when_not_provided_defaults_to_skip_total(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {"data": [], "total_count": 0}

        with patch("routers.actresses.get_info_client", return_value=mock_client):
            result = await actresses.get_actress_videos(actress_id=123, page=1, page_size=20)

        mock_client.get_actress_videos.assert_awaited_once_with(
            123, page=1, page_size=20,
            include_supplement=None, service_code=None, year=None, sort_by=None, include_total=False,
        )
        self.assertEqual(result["data"], [])

    async def test_actress_videos_groups_variants_by_default(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.return_value = {
            "data": [
                {"content_id": "miaa00784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                {"content_id": "miaa00784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title （BOD）", "service_code": "mono"},
            ],
            "total_count": 2,
            "total_pages": 1,
        }
        translator = AsyncMock()
        translator.translate_videos.side_effect = lambda items, **_kwargs: items

        with (
            patch("routers.actresses.get_info_client", return_value=mock_client),
            patch("routers.actresses.get_translator_service", return_value=translator),
        ):
            result = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                variant_mode="grouped",
                include_variant_explanations=True,
            )

        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["variant_group_count"], 2)
        self.assertIn("variant_group_items", result["data"][0])

    async def test_actress_videos_indexed_scope_uses_index_and_cache_key_includes_scope(self):
        mock_client = AsyncMock()
        mock_client.get_actress_videos.side_effect = [
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                ],
                "total_count": 1,
                "total_pages": 1,
            },
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                ],
                "total_count": 1,
                "total_pages": 1,
            },
        ]
        translator = AsyncMock()
        translator.translate_videos.side_effect = lambda items, **_kwargs: items

        def apply_index(items, **_kwargs):
            row = dict(items[0])
            row["variant_indexed"] = True
            row["variant_group_count"] = 4
            row["variant_group_items"] = [{"content_id": "miaa00784", "display_code": "MIAA-784"}]
            return [row]

        with (
            patch("routers.actresses.get_info_client", return_value=mock_client),
            patch("routers.actresses.get_translator_service", return_value=translator),
            patch("routers.actresses.apply_indexed_variant_groups", side_effect=apply_index) as indexed,
        ):
            indexed_result = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                variant_mode="grouped",
                variant_scope="indexed",
            )
            page_result = await actresses.get_actress_videos(
                actress_id=123,
                page=1,
                page_size=20,
                include_supplement="1",
                variant_mode="grouped",
                variant_scope="page",
            )

        self.assertTrue(indexed_result["data"][0]["variant_indexed"])
        self.assertEqual(indexed_result["data"][0]["variant_group_count"], 4)
        self.assertFalse(page_result["data"][0].get("variant_indexed", False))
        indexed.assert_called_once()
        self.assertEqual(mock_client.get_actress_videos.await_count, 2)

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


class ActressVideosCacheBypassTest(FakeRedisMixin, unittest.TestCase):
    def test_cache_zero_bypasses_cached_actress_videos_response(self):
        app = FastAPI()
        app.include_router(actresses.router)
        mock_client = AsyncMock()
        mock_client.get_actress_videos.side_effect = [
            {"data": [{"content_id": "old", "title_ja": "旧"}], "total_count": -1},
            {"data": [{"content_id": "fresh", "title_ja": "新"}], "total_count": -1},
        ]
        translator = AsyncMock()
        translator.translate_videos.side_effect = lambda items, **_kwargs: items

        with (
            patch("routers.actresses.get_info_client", return_value=mock_client),
            patch("routers.actresses.get_translator_service", return_value=translator),
        ):
            client = create_test_client(app)
            first = client.get("/api/v1/actresses/123/videos?include_supplement=1")
            cached = client.get("/api/v1/actresses/123/videos?include_supplement=1")
            fresh = client.get("/api/v1/actresses/123/videos?include_supplement=1&cache=0")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(first.json()["data"][0]["content_id"], "old")
        self.assertEqual(cached.json()["data"][0]["content_id"], "old")
        self.assertEqual(fresh.json()["data"][0]["content_id"], "fresh")
        self.assertEqual(mock_client.get_actress_videos.await_count, 2)


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
            response = create_test_client(app).post(
                "/api/v1/actresses/batch_videos",
                json={"ids": [26225], "page": 2, "page_size": 3},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["26225"]["total_count"], 1)
        mock_client.batch_get_actress_videos.assert_awaited_once_with([26225], page=2, page_size=3)
        translator.translate_videos.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
