from __future__ import annotations

import asyncio
import unittest
import httpx
from unittest.mock import AsyncMock, patch

from modules.info_client import InfoClient


class InfoClientVideoDetailTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_video_returns_javinfo_detail_without_metatube(self):
        client = InfoClient()
        javinfo_detail = {
            "dvd_id": "MIAA-784",
            "title_ja": "Full title",
            "jacket_thumb_url": "digital/video/miaa00784/miaa00784ps",
        }

        with patch("services.cache.get_video", return_value=None), \
             patch("services.cache.set_video") as set_cache, \
             patch.object(client, "_get", AsyncMock(return_value=javinfo_detail)) as get_mock, \
             patch.object(client, "proxy_post", AsyncMock(return_value={"job_id": 1})) as post_mock:
            data = await client.get_video("MIAA-784")
            await asyncio.sleep(0)

        get_mock.assert_awaited_once_with("/api/v1/videos/miaa784", params=None)
        post_mock.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": "all", "source_movie_id": "MIAA-784"},
        )
        self.assertEqual(set_cache.call_args.kwargs["ttl"], 300)
        self.assertEqual(data["content_id"], "MIAA-784")
        self.assertEqual(data["title_ja"], "Full title")
        self.assertNotIn("summary", data)
        self.assertNotIn("director", data)
        self.assertNotIn("score", data)
        self.assertNotIn("meta_provider", data)

    async def test_get_video_preserves_javinfo_enhancement_fields_from_cache(self):
        cached = {
            "content_id": "MIAA-784",
            "title_ja": "Cached title",
            "summary": "JavInfo summary",
            "score": 4.2,
            "meta_provider": "mgstage",
        }
        client = InfoClient()

        with patch("services.cache.get_video", return_value=cached), \
             patch("services.cache.set_video"):
            data = await client.get_video("MIAA-784")

        self.assertEqual(data["content_id"], "MIAA-784")
        self.assertEqual(data["title_ja"], "Cached title")
        self.assertEqual(data["summary"], "JavInfo summary")
        self.assertEqual(data["score"], 4.2)
        self.assertEqual(data["meta_provider"], "mgstage")
        self.assertNotIn("director", data)

    async def test_get_video_refreshes_cached_partial_enhancement_fields(self):
        cached = {
            "content_id": "MIAA-935",
            "title_ja": "Cached title",
            "summary": "Cached summary",
            "meta_provider": "fanza",
        }
        javinfo_detail = {
            "content_id": "miaa935",
            "dvd_id": "MIAA-935",
            "title_ja": "Fresh title",
            "summary": "Fresh summary",
            "score": 4.71,
            "meta_provider": "fanza",
        }
        client = InfoClient()

        with patch("services.cache.get_video", return_value=cached), \
             patch("services.cache.set_video") as set_cache, \
             patch.object(client, "_get", AsyncMock(return_value=javinfo_detail)) as get_mock, \
             patch.object(client, "proxy_post", AsyncMock()) as post_mock:
            data = await client.get_video("MIAA-935")
            await asyncio.sleep(0)

        get_mock.assert_awaited_once_with("/api/v1/videos/miaa935", params=None)
        post_mock.assert_not_awaited()
        self.assertEqual(data["summary"], "Fresh summary")
        self.assertEqual(data["score"], 4.71)
        self.assertEqual(data["meta_provider"], "fanza")
        set_cache.assert_called_once()
        self.assertEqual(set_cache.call_args.args[0], "miaa935")
        self.assertEqual(set_cache.call_args.kwargs["ttl"], 86400)

    async def test_get_video_requeues_cached_detail_without_enhancement_and_shortens_ttl(self):
        cached = {
            "content_id": "MIAA-784",
            "title_ja": "Cached title",
        }
        client = InfoClient()

        with patch("services.cache.get_video", return_value=cached), \
             patch("services.cache.set_video") as set_cache, \
             patch.object(client, "proxy_post", AsyncMock(return_value={"job_id": 1})) as post_mock:
            data = await client.get_video("MIAA-784")
            await asyncio.sleep(0)

        self.assertEqual(data["title_ja"], "Cached title")
        set_cache.assert_called_once_with("miaa784", cached, ttl=300)
        post_mock.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": "all", "source_movie_id": "MIAA-784"},
        )

    async def test_get_video_does_not_queue_enrichment_when_javinfo_has_enhancement_fields(self):
        client = InfoClient()
        javinfo_detail = {
            "dvd_id": "MIAA-784",
            "title_ja": "Full title",
            "summary": "JavInfo summary",
            "score": 4.2,
            "meta_provider": "mgstage",
        }

        with patch("services.cache.get_video", return_value=None), \
             patch("services.cache.set_video"), \
             patch.object(client, "_get", AsyncMock(return_value=javinfo_detail)), \
             patch.object(client, "proxy_post", AsyncMock()) as post_mock:
            data = await client.get_video("MIAA-784")
            await asyncio.sleep(0)

        post_mock.assert_not_awaited()
        self.assertEqual(data["summary"], "JavInfo summary")
        self.assertEqual(data["score"], 4.2)

    async def test_get_video_uses_service_code_in_cache_key(self):
        client = InfoClient()
        javinfo_detail = {
            "dvd_id": "MIAA-784",
            "title_ja": "Digital detail",
        }

        with patch("services.cache.get_video", return_value=None) as get_cache, \
             patch("services.cache.set_video") as set_cache, \
             patch.object(client, "_get", AsyncMock(return_value=javinfo_detail)):
            await client.get_video("MIAA-784", service_code="digital")

        get_cache.assert_called_once_with("miaa784:service:digital")
        set_cache.assert_called_once()
        self.assertEqual(set_cache.call_args.args[0], "miaa784:service:digital")

    async def test_random_search_delegates_to_javinfo_without_cache(self):
        client = InfoClient()
        random_result = {
            "data": [{"dvd_id": "MIAA-784", "jacket_thumb_url": "digital/video/miaa00784/miaa00784ps"}],
            "page": 1,
            "page_size": 30,
            "total_count": 1866871,
            "total_pages": 62230,
        }

        with patch.object(client, "_get", AsyncMock(return_value=random_result)) as get_mock, \
             patch("services.cache.get_search", return_value=None) as get_cache, \
             patch("services.cache.set_search") as set_cache:
            data = await client.search_videos(category_id=5023, random="1", page=1, page_size=30)

        get_mock.assert_awaited_once()
        params = get_mock.await_args.args[1]
        self.assertEqual(params["random"], "1")
        self.assertEqual(params["category_id"], 5023)
        self.assertEqual(params["page"], 1)
        self.assertEqual(params["page_size"], 30)
        get_cache.assert_not_called()
        set_cache.assert_not_called()
        self.assertEqual(data["data"][0]["content_id"], "MIAA-784")
        self.assertEqual(data["data"][0]["jacket_thumb_url"], "https://pics.dmm.co.jp/digital/video/miaa00784/miaa00784ps.jpg")

    async def test_random_search_does_not_fallback_to_non_random_pages(self):
        client = InfoClient()
        request = httpx.Request("GET", "http://example.test/api/v1/videos/search")
        response = httpx.Response(
            400,
            request=request,
            json={"error": "random=1 requires at least one filter"},
        )
        error = httpx.HTTPStatusError("Bad Request", request=request, response=response)

        with patch.object(client, "_get", AsyncMock(side_effect=error)) as get_mock, \
             patch("services.cache.get_search") as get_cache, \
             patch("services.cache.set_search") as set_cache:
            with self.assertRaises(httpx.HTTPStatusError):
                await client.search_videos(random="1", page=1, page_size=30)

        get_mock.assert_awaited_once()
        get_cache.assert_not_called()
        set_cache.assert_not_called()

    async def test_run_migrations_uses_admin_endpoint_with_long_timeout(self):
        client = InfoClient()

        with patch.object(client, "proxy_post_long", AsyncMock(return_value={"ok": True})) as post_mock:
            result = await client.run_migrations()

        self.assertEqual(result, {"ok": True})
        post_mock.assert_awaited_once_with("/api/v1/admin/migrations", {"dry_run": False})


if __name__ == "__main__":
    unittest.main()
