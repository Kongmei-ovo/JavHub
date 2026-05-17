from __future__ import annotations

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
             patch("services.cache.set_video"), \
             patch.object(client, "_get", AsyncMock(return_value=javinfo_detail)) as get_mock, \
             patch("modules.metatube_client.get_movie", new_callable=AsyncMock) as metatube_mock:
            data = await client.get_video("MIAA-784")

        get_mock.assert_awaited_once_with("/api/v1/videos/miaa784", params=None)
        metatube_mock.assert_not_awaited()
        self.assertEqual(data["content_id"], "MIAA-784")
        self.assertEqual(data["title_ja"], "Full title")
        self.assertNotIn("summary", data)
        self.assertNotIn("director", data)
        self.assertNotIn("score", data)
        self.assertNotIn("meta_provider", data)

    async def test_get_video_strips_legacy_metatube_fields_from_cached_detail(self):
        cached = {
            "content_id": "MIAA-784",
            "title_ja": "Cached title",
            "summary": "legacy summary",
            "director": "legacy director",
            "score": 4.2,
            "meta_provider": "metatube",
        }
        client = InfoClient()

        with patch("services.cache.get_video", return_value=cached), \
             patch("services.cache.set_video"):
            data = await client.get_video("MIAA-784")

        self.assertEqual(data["content_id"], "MIAA-784")
        self.assertEqual(data["title_ja"], "Cached title")
        self.assertNotIn("summary", data)
        self.assertNotIn("director", data)
        self.assertNotIn("score", data)
        self.assertNotIn("meta_provider", data)

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

    async def test_get_video_metadata_returns_only_metatube_enhancement_fields(self):
        client = InfoClient()
        metatube_detail = {
            "title": "Ignored title",
            "summary": "Metadata summary",
            "director": "Metadata director",
            "score": 4.5,
            "provider": "metatube",
            "actors": ["ignored"],
        }

        with patch("modules.metatube_client.get_movie", AsyncMock(return_value=metatube_detail)) as metatube_mock:
            data = await client.get_video_metadata("MIAA-784")

        metatube_mock.assert_awaited_once_with("MIAA-784")
        self.assertEqual(data, {
            "summary": "Metadata summary",
            "director": "Metadata director",
            "score": 4.5,
            "meta_provider": "metatube",
        })

    async def test_get_video_metadata_returns_empty_dict_on_failure(self):
        client = InfoClient()

        with patch("modules.metatube_client.get_movie", AsyncMock(side_effect=Exception("Not Found"))):
            data = await client.get_video_metadata("MIAA-784")

        self.assertEqual(data, {})

    async def test_random_search_falls_back_when_upstream_rejects_large_result_set(self):
        client = InfoClient()
        request = httpx.Request("GET", "http://example.test/api/v1/videos/search")
        limited_response = httpx.Response(
            400,
            request=request,
            json={"error": "random=1 is limited to filtered result sets of 5000 rows or fewer"},
        )
        fallback_result = {
            "data": [{"dvd_id": "MIAA-784", "jacket_thumb_url": "digital/video/miaa00784/miaa00784ps"}],
            "total_count": 6000,
        }
        get_mock = AsyncMock(side_effect=[
            httpx.HTTPStatusError("Bad Request", request=request, response=limited_response),
            fallback_result,
        ])

        with patch.object(client, "_get", get_mock), \
             patch("services.cache.get_search", return_value=None), \
             patch("services.cache.set_search") as set_search:
            data = await client.search_videos(category_id=5023, random="1", page=1, page_size=30)

        self.assertEqual(data["total_count"], 6000)
        self.assertEqual(data["data"][0]["content_id"], "MIAA-784")
        self.assertEqual(get_mock.await_count, 2)
        self.assertNotIn("random", get_mock.await_args_list[1].args[1])
        set_search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
