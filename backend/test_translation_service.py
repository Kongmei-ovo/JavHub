from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


class TempDbMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.base_patch = patch("database.base.DB_PATH", self.db_path)
        self.base_patch.start()
        from database import init_db
        init_db()

    def tearDown(self):
        self.base_patch.stop()
        self.tmp.cleanup()


class TranslatorServiceTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    def service(self):
        from translations.service import TranslatorService

        return TranslatorService({
            "enabled": True,
            "target_language": "zh-CN",
            "provider_order": ["cache", "mapping", "openai_compatible"],
            "openai_compatible": {
                "base_url": "https://api.example.test/v1",
                "api_key": "secret",
                "model": "test-model",
                "timeout": 3,
            },
        })

    async def test_cache_hit_does_not_request_ai(self):
        from database import upsert_cached_translation
        from translations.providers import OpenAICompatibleProvider

        upsert_cached_translation("summary:MIAA-784", "原文", "缓存译文", "openai_compatible", "test-model")

        with patch.object(OpenAICompatibleProvider, "translate", new_callable=AsyncMock) as ai_translate:
            translated = await self.service().translate_text("原文", scope="summary:MIAA-784", use_ai=True)

        self.assertEqual(translated, "缓存译文")
        ai_translate.assert_not_awaited()

    async def test_mapping_precedes_ai(self):
        from translations.providers import OpenAICompatibleProvider

        with patch.object(OpenAICompatibleProvider, "translate", new_callable=AsyncMock) as ai_translate:
            translated = await self.service().translate_text(
                "女優",
                scope="category:1",
                mapping={"女優": "演员"},
                use_ai=True,
            )

        self.assertEqual(translated, "演员")
        ai_translate.assert_not_awaited()

    async def test_ai_success_is_persisted(self):
        from database import get_cached_translation
        from translations.providers import OpenAICompatibleProvider, TranslationResult

        with patch.object(
            OpenAICompatibleProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("AI 译文", "openai_compatible", "test-model")),
        ):
            translated = await self.service().translate_text("原文", scope="summary:MIAA-784", use_ai=True)

        self.assertEqual(translated, "AI 译文")
        cached = get_cached_translation("summary:MIAA-784", "原文")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["translated_text"], "AI 译文")

    async def test_ai_failure_falls_back_to_original(self):
        from translations.providers import OpenAICompatibleProvider

        with patch.object(OpenAICompatibleProvider, "translate", AsyncMock(return_value=None)):
            translated = await self.service().translate_text("原文", scope="summary:MIAA-784", use_ai=True)

        self.assertEqual(translated, "原文")

    async def test_video_translation_omits_same_as_original_fields(self):
        from translations.providers import OpenAICompatibleProvider

        with patch.object(OpenAICompatibleProvider, "translate", AsyncMock(return_value=None)):
            data = await self.service().translate_video(
                "MIAA-784",
                {"content_id": "MIAA-784", "title_ja": "原文", "summary": "简介"},
                use_ai=True,
            )

        self.assertNotIn("title_ja_translated", data)
        self.assertNotIn("summary_translated", data)

    async def test_batch_provider_order_skips_ai(self):
        from translations.providers import GoogleFreeProvider, OpenAICompatibleProvider, TranslationResult

        service = self.service()
        with patch.object(
            GoogleFreeProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("廉价译文", "google_free")),
        ) as google_translate, patch.object(OpenAICompatibleProvider, "translate", new_callable=AsyncMock) as ai_translate:
            translated = await service.translate_text(
                "原文",
                scope="title:MIAA-784:title_ja",
                use_ai=False,
                provider_order=["cache", "google_free", "openai_compatible"],
            )

        self.assertEqual(translated, "廉价译文")
        google_translate.assert_awaited_once()
        ai_translate.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
