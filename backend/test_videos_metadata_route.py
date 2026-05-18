from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from fastapi.routing import APIRoute
from routers.videos import router, search_videos


class VideosMetadataRouteTest(unittest.IsolatedAsyncioTestCase):
    def test_metadata_route_is_not_registered(self):
        paths = [route.path for route in router.routes if isinstance(route, APIRoute)]

        self.assertNotIn("/api/v1/videos/{content_id}/metadata", paths)
        self.assertIn("/api/v1/videos/{content_id}", paths)

    async def test_search_route_uses_cache_only_translation(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [{"content_id": "miaa784", "title_ja": "原文"}],
            "total_count": 1,
            "total_pages": 1,
        }
        translator = AsyncMock()
        translator.translate_video.return_value = {"content_id": "miaa784", "title_ja": "原文"}

        kwargs = {
            "q": None,
            "content_id": None,
            "dvd_id": None,
            "maker_id": None,
            "maker_name": None,
            "series_id": None,
            "series_name": None,
            "actress_id": 26225,
            "actress_name": None,
            "category_id": None,
            "category_name": None,
            "label_id": None,
            "label_name": None,
            "site_id": None,
            "year": None,
            "year_from": None,
            "year_to": None,
            "runtime_min": None,
            "runtime_max": None,
            "release_date_from": None,
            "release_date_to": None,
            "service_code": None,
            "sort_by": None,
            "sort_order": None,
            "random": "1",
            "page": 1,
            "page_size": 30,
        }

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            data = await search_videos(**kwargs)

        self.assertEqual(data["total_count"], 1)
        translator.translate_video.assert_awaited_once()
        self.assertFalse(translator.translate_video.await_args.kwargs["allow_network"])

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
        self.assertEqual(translator.seen_order, ["ai"])
        self.assertEqual(translator.settings["provider_order"], ["cache", "mapping", "openai_compatible"])

    async def test_ai_model_test_route_uses_current_config(self):
        from routers.config import test_ai_model

        with patch("config.Config.ai", new_callable=PropertyMock, return_value={
            "provider": "gemini",
            "openai_compatible": {},
            "gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": "saved-key",
                "model": "saved-model",
                "timeout": 3,
            },
            "ollama": {},
        }), patch("routers.config.build_ai_client") as build_client:
            client = AsyncMock()
            client.test.return_value = {
                "success": True,
                "provider": "gemini",
                "model": "current-model",
                "reply": "ok",
                "latency_ms": 12,
            }
            build_client.return_value = client
            result = await test_ai_model({
                "provider": "gemini",
                "ai": {
                    "gemini": {
                        "base_url": "https://current.example/v1beta",
                        "api_key": "",
                        "model": "current-model",
                        "timeout": 5,
                    }
                },
            })

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "current-model")
        self.assertEqual(result["reply"], "ok")
        sent = build_client.call_args.args[0]
        self.assertEqual(sent["provider"], "gemini")
        self.assertEqual(sent["gemini"]["base_url"], "https://current.example/v1beta")
        self.assertEqual(sent["gemini"]["api_key"], "saved-key")
        self.assertEqual(sent["gemini"]["model"], "current-model")

    async def test_ai_models_route_lists_models_with_draft_config(self):
        from routers.config import list_ai_models

        with patch("config.Config.ai", new_callable=PropertyMock, return_value={
            "provider": "openai_compatible",
            "openai_compatible": {
                "base_url": "https://saved.example/v1",
                "api_key": "saved-key",
                "model": "saved-model",
                "timeout": 3,
            },
            "gemini": {},
            "ollama": {},
        }), patch("routers.config.build_ai_client") as build_client:
            client = AsyncMock()
            client.list_models.return_value = {
                "provider": "openai_compatible",
                "models": [{"id": "draft-model", "name": "draft-model"}],
            }
            build_client.return_value = client
            result = await list_ai_models({
                "provider": "openai_compatible",
                "ai": {
                    "openai_compatible": {
                        "base_url": "https://draft.example/v1",
                        "api_key": "",
                        "model": "draft-model",
                    }
                },
            })

        self.assertEqual(result["models"][0]["id"], "draft-model")
        sent = build_client.call_args.args[0]
        self.assertEqual(sent["openai_compatible"]["base_url"], "https://draft.example/v1")
        self.assertEqual(sent["openai_compatible"]["api_key"], "saved-key")

    async def test_legacy_ai_test_body_still_uses_openai_compatible(self):
        from routers.config import test_ai_model

        with patch("config.Config.ai", new_callable=PropertyMock, return_value={
            "provider": "gemini",
            "openai_compatible": {
                "base_url": "https://saved.example/v1",
                "api_key": "saved-key",
                "model": "saved-model",
                "timeout": 3,
            },
            "gemini": {},
            "ollama": {},
        }), patch("routers.config.build_ai_client") as build_client:
            client = AsyncMock()
            client.test.return_value = {
                "success": True,
                "provider": "openai_compatible",
                "model": "current-model",
                "reply": "ok",
                "latency_ms": 12,
            }
            build_client.return_value = client
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
        sent = build_client.call_args.args[0]
        self.assertEqual(sent["provider"], "openai_compatible")
        self.assertEqual(sent["openai_compatible"]["base_url"], "https://current.example/v1")
        self.assertEqual(sent["openai_compatible"]["api_key"], "saved-key")


if __name__ == "__main__":
    unittest.main()
