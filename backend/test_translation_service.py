from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
        from translations.providers import AIProvider, TranslationResult

        with patch.object(
            AIProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("AI 译文", "ai", "test-model")),
        ):
            translated = await self.service().translate_text(
                "原文",
                scope="summary:MIAA-784",
                use_ai=True,
                provider_order=["ai"],
            )

        self.assertEqual(translated, "AI 译文")
        cached = get_cached_translation("summary:MIAA-784", "原文")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["translated_text"], "AI 译文")

    async def test_legacy_openai_provider_key_uses_shared_ai_provider(self):
        from translations.providers import AIProvider, TranslationResult

        with patch.object(
            AIProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("AI 译文", "gemini", "gemini-test")),
        ) as ai_translate:
            translated = await self.service().translate_text(
                "原文",
                scope="summary:MIAA-784",
                use_ai=True,
                provider_order=["openai_compatible"],
            )

        self.assertEqual(translated, "AI 译文")
        ai_translate.assert_awaited_once()

    async def test_ai_provider_uses_scene_specific_prompt_for_title_scope(self):
        from translations.providers import AIProvider, TranslationRequest

        captured = {}

        class FakeClient:
            async def chat(self, messages, **kwargs):
                captured["messages"] = messages
                captured["kwargs"] = kwargs
                return SimpleNamespace(content="中文标题", provider="gemini", model="gemini-test")

        request = TranslationRequest(
            text="MIAA-784 kawaii*卒業",
            scope="title:MIAA-784:title_ja",
            target_language="zh-CN",
        )
        with patch("translations.providers.build_ai_client", return_value=FakeClient()):
            result = await AIProvider({"provider": "gemini", "gemini": {"model": "gemini-test"}}).translate(request)

        self.assertEqual(result.translated_text, "中文标题")
        system_prompt = captured["messages"][0]["content"]
        user_prompt = captured["messages"][1]["content"]
        self.assertIn("adult video title", system_prompt)
        self.assertIn("not an advertisement", system_prompt)
        self.assertIn("Preserve product codes", system_prompt)
        self.assertNotIn(request.text, system_prompt)
        self.assertIn("Source text:", user_prompt)
        self.assertTrue(user_prompt.rstrip().endswith(request.text))

    async def test_ai_provider_uses_scene_specific_prompts_for_metadata_types(self):
        from translations.providers import AIProvider, TranslationRequest

        cases = [
            (
                TranslationRequest(text="痴女", scope="category:1", context="category name"),
                ["adult video genre/tag", "short noun phrase", "Do not explain the tag"],
            ),
            (
                TranslationRequest(text="三上悠亜", scope="actress:1", context="actress name"),
                ["performer name", "Preserve the name", "Do not invent phonetic transliterations"],
            ),
            (
                TranslationRequest(text="あらすじ", scope="summary:MIAA-784"),
                ["summary/description", "Translate all meaning faithfully", "Do not censor explicit terms"],
            ),
            (
                TranslationRequest(text="普通のメタデータ", scope="unknown:1", context="unknown metadata"),
                ["metadata field", "Return only the translated text"],
            ),
        ]

        class FakeClient:
            async def chat(self, messages, **kwargs):
                self.messages = messages
                return SimpleNamespace(content="译文", provider="ollama", model="qwen")

        for request, expected_fragments in cases:
            with self.subTest(scope=request.scope, context=request.context):
                client = FakeClient()
                with patch("translations.providers.build_ai_client", return_value=client):
                    result = await AIProvider({"provider": "ollama", "ollama": {"model": "qwen"}}).translate(request)

                self.assertEqual(result.translated_text, "译文")
                system_prompt = client.messages[0]["content"]
                for fragment in expected_fragments:
                    self.assertIn(fragment, system_prompt)

    async def test_translate_video_passes_contextual_prompts_to_ai_provider(self):
        calls = []

        class FakeClient:
            async def chat(self, messages, **kwargs):
                calls.append(messages)
                return SimpleNamespace(content=f"译文{len(calls)}", provider="openai_compatible", model="test-model")

        with patch("translations.providers.build_ai_client", return_value=FakeClient()):
            data = await self.service().translate_video(
                "MIAA-784",
                {
                    "content_id": "MIAA-784",
                    "title_ja": "タイトル",
                    "summary": "紹介文",
                    "categories": [{"id": 100, "name_ja": "痴女"}],
                },
                use_ai=True,
            )

        self.assertEqual(data["title_ja_translated"], "译文2")
        self.assertEqual(data["summary_translated"], "译文3")
        prompts = [messages[0]["content"] for messages in calls]
        self.assertIn("adult video genre/tag", prompts[0])
        self.assertIn("adult video title", prompts[1])
        self.assertIn("summary/description", prompts[2])

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

    async def test_video_translation_sanitizes_masked_text_in_localized_fields(self):
        from database import upsert_translation

        upsert_translation("category:7", {"category": {"A***e": "肛门"}})

        data = await self.service().translate_video(
            "MIAA-784",
            {
                "content_id": "MIAA-784",
                "title_ja": "kawaii*卒業",
                "categories": [{"id": 7, "name_en": "A***e"}],
            },
            allow_network=False,
        )

        self.assertEqual(data["title_ja"], "kawaii*卒業")
        self.assertEqual(data["categories"][0]["name_en"], "肛门")
        self.assertEqual(data["categories"][0]["name_en_translated"], "肛门")

    async def test_category_entities_decensor_stale_masked_names_before_mapping(self):
        from database import upsert_translation

        upsert_translation("category:5064", {"category": {"Hypnotism": "催眠"}})

        data = await self.service().translate_entities(
            [{"id": 5064, "name_en": "H*******m"}],
            entity_type="category",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )

        self.assertEqual(data[0]["name_en"], "Hypnotism")
        self.assertEqual(data[0]["name_en_translated"], "催眠")

    async def test_category_entities_decensor_name_en_when_name_ja_drives_mapping(self):
        from database import upsert_translation

        upsert_translation("category:4058", {"category": {"ショタ": "正太"}})

        data = await self.service().translate_entities(
            [{"id": 4058, "name_en": "S******n", "name_ja": "ショタ"}],
            entity_type="category",
            keys=["name_ja", "name_en", "name"],
            allow_network=False,
        )

        self.assertEqual(data[0]["name_en"], "Shotacon")
        self.assertEqual(data[0]["name_ja"], "ショタ")
        self.assertEqual(data[0]["name_ja_translated"], "正太")

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

    async def test_allow_network_false_skips_external_providers(self):
        from translations.providers import GoogleFreeProvider

        service = self.service()
        with patch.object(GoogleFreeProvider, "translate", new_callable=AsyncMock) as google_translate:
            translated = await service.translate_text(
                "原文",
                scope="title:MIAA-784:title_ja",
                use_ai=False,
                provider_order=["cache", "mapping", "google_free"],
                allow_network=False,
            )

        self.assertEqual(translated, "原文")
        google_translate.assert_not_awaited()

    async def test_provider_same_as_source_can_be_cached_for_batch_skip(self):
        from database import get_cached_translation
        from translations.providers import GoogleFreeProvider, TranslationResult

        with patch.object(
            GoogleFreeProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("原文", "google_free")),
        ):
            translated = await self.service().translate_text(
                "原文",
                scope="title:MIAA-784:title_ja",
                use_ai=False,
                provider_order=["google_free"],
                return_original=False,
            )

        self.assertEqual(translated, "原文")
        cached = get_cached_translation("title:MIAA-784:title_ja", "原文")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["translated_text"], "原文")


if __name__ == "__main__":
    unittest.main()
