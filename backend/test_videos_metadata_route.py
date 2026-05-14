from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from fastapi.routing import APIRoute
from routers.videos import get_video_metadata, router


class VideosMetadataRouteTest(unittest.IsolatedAsyncioTestCase):
    def test_metadata_route_is_registered_before_content_id_route(self):
        paths = [route.path for route in router.routes if isinstance(route, APIRoute)]

        self.assertLess(paths.index("/api/v1/videos/{content_id}/metadata"), paths.index("/api/v1/videos/{content_id}"))

    async def test_metadata_route_calls_get_video_metadata_not_get_video(self):
        client = AsyncMock()
        client.get_video_metadata.return_value = {"summary": "Metadata summary"}
        translator = AsyncMock()
        translator.translate_metadata.return_value = {
            "summary": "Metadata summary",
            "summary_translated": "译文",
        }

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            data = await get_video_metadata("MIAA-784")

        client.get_video_metadata.assert_awaited_once_with("MIAA-784")
        client.get_video.assert_not_called()
        translator.translate_metadata.assert_awaited_once_with("MIAA-784", {"summary": "Metadata summary"})
        self.assertEqual(data, {"summary": "Metadata summary", "summary_translated": "译文"})

    async def test_metadata_route_keeps_original_when_translation_falls_back(self):
        client = AsyncMock()
        client.get_video_metadata.return_value = {"summary": "Metadata summary"}
        translator = AsyncMock()
        translator.translate_metadata.return_value = {"summary": "Metadata summary"}

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            data = await get_video_metadata("MIAA-784")

        self.assertEqual(data, {"summary": "Metadata summary"})

    async def test_translation_test_route_uses_ai_provider_only(self):
        from routers.translation import test_translation

        class Translator:
            def __init__(self):
                self.settings = {"provider_order": ["cache", "mapping", "openai_compatible"]}
                self.seen_order = None

            async def translate_text(self, *args, **kwargs):
                self.seen_order = list(self.settings["provider_order"])
                return "译文"

        translator = Translator()
        with patch("routers.translation.get_translator_service", return_value=translator):
            result = await test_translation({"text": "原文"})

        self.assertEqual(result["translated_text"], "译文")
        self.assertEqual(translator.seen_order, ["openai_compatible"])
        self.assertEqual(translator.settings["provider_order"], ["cache", "mapping", "openai_compatible"])

    async def test_ai_model_test_route_uses_current_config(self):
        from routers.config import test_ai_model

        class FakeResponse:
            status_code = 200
            text = ""

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        class FakeAsyncClient:
            captured = {}

            def __init__(self, *args, **kwargs):
                FakeAsyncClient.captured["timeout"] = kwargs.get("timeout")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, json=None, headers=None):
                FakeAsyncClient.captured.update({"url": url, "json": json, "headers": headers})
                return FakeResponse()

        with patch("config.Config.openai_compatible", new_callable=PropertyMock, return_value={
            "base_url": "https://saved.example/v1",
            "api_key": "saved-key",
            "model": "saved-model",
            "timeout": 3,
        }), patch("httpx.AsyncClient", FakeAsyncClient):
            result = await test_ai_model({
                "openai_compatible": {
                    "base_url": "https://current.example/v1",
                    "api_key": "",
                    "model": "current-model",
                    "timeout": 5,
                }
            })

        self.assertTrue(result["success"])
        self.assertEqual(result["model"], "current-model")
        self.assertEqual(result["reply"], "ok")
        self.assertEqual(FakeAsyncClient.captured["url"], "https://current.example/v1/chat/completions")
        self.assertEqual(FakeAsyncClient.captured["json"]["model"], "current-model")
        self.assertEqual(FakeAsyncClient.captured["headers"]["Authorization"], "Bearer saved-key")
        self.assertEqual(FakeAsyncClient.captured["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
