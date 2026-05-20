from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs


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

    async def test_bulk_translation_lookup_matches_single_lookup(self):
        from database import get_translation, get_translations_bulk, upsert_translation

        upsert_translation("category:4058", {"category": {"ショタ": "正太"}})
        upsert_translation("_global:label:7", {"label": {"企画": "企划"}})

        bulk = get_translations_bulk(["category:4058", "label:7", "missing:1"])

        self.assertEqual(bulk["category:4058"], get_translation("category:4058"))
        self.assertEqual(bulk["label:7"], get_translation("label:7"))
        self.assertIsNone(bulk["missing:1"])

    async def test_bulk_translation_lookup_caches_direct_and_fallback_misses(self):
        import database.translation as translation_module

        translation_module._translation_cache.clear()
        with patch.object(translation_module, "_load_translation_rows", return_value={}) as load_rows:
            first = translation_module.get_translations_bulk(["missing:1"])
            second = translation_module.get_translations_bulk(["missing:1"])

        self.assertIsNone(first["missing:1"])
        self.assertIsNone(second["missing:1"])
        self.assertEqual(load_rows.call_count, 2)

    async def test_translate_entities_prefetches_mappings_in_bulk(self):
        from translations import service as service_module

        service = self.service()
        items = [
            {"id": 1, "name_ja": "企画"},
            {"id": 2, "name_ja": "単体"},
        ]

        with patch.object(
            service_module,
            "get_translations_bulk",
            return_value={
                "label:1": {"label": {"企画": "企划"}},
                "label:2": {"label": {"単体": "单体"}},
            },
        ) as bulk_lookup:
            data = await service.translate_entities(
                items,
                entity_type="label",
                keys=["name_ja", "name_en", "name"],
                allow_network=False,
            )

        bulk_lookup.assert_called_once_with(["label:1", "label:2"])
        self.assertEqual(data[0]["name_ja_translated"], "企划")
        self.assertEqual(data[1]["name_ja_translated"], "单体")

    async def test_translate_entities_uses_each_entity_scope_for_translation_cache(self):
        from translations import service as service_module

        service = self.service()
        service.translate_text = AsyncMock(side_effect=lambda text, **_kwargs: text)

        with patch.object(service_module, "get_translations_bulk", return_value={}):
            await service.translate_entities(
                [
                    {"id": 1, "name_ja": "企画"},
                    {"id": 2, "name_ja": "単体"},
                ],
                entity_type="label",
                keys=["name_ja", "name_en", "name"],
                allow_network=False,
            )

        scopes = [call.kwargs["scope"] for call in service.translate_text.await_args_list]
        self.assertEqual(scopes, ["label:1", "label:2"])

    async def test_translate_videos_prefetches_content_and_entity_mappings_in_bulk(self):
        from translations import service as service_module

        service = self.service()
        videos = [
            {
                "content_id": "MIAA-784",
                "title_ja": "タイトルA",
                "categories": [{"id": 7, "name_ja": "痴女"}],
                "maker": {"id": 11, "name_ja": "メーカー"},
                "series": {"id": 12, "name": "シリーズ"},
                "label": {"id": 13, "name_ja": "レーベル"},
                "actresses": [{"id": 26225, "name_ja": "三上悠亜"}],
            },
            {
                "content_id": "MIAA-785",
                "title_ja": "タイトルB",
                "categories": [{"id": 8, "name_ja": "企画"}],
                "maker": {"id": 11, "name_ja": "メーカー"},
            },
        ]

        with patch.object(
            service_module,
            "get_translations_bulk",
            return_value={
                "MIAA-784": {"title": {"タイトルA": "标题A"}},
                "MIAA-785": {"title": {"タイトルB": "标题B"}},
                "category:7": {"category": {"痴女": "痴女中文"}},
                "category:8": {"category": {"企画": "企划"}},
                "maker:11": {"maker": {"メーカー": "片商"}},
                "series:12": {"series": {"シリーズ": "系列"}},
                "label:13": {"label": {"レーベル": "厂牌"}},
                "actress:26225": {"actress": {"三上悠亜": "三上悠亚"}},
            },
        ) as bulk_lookup:
            result = await service.translate_videos(videos, allow_network=False)

        requested = bulk_lookup.call_args.args[0]
        self.assertIn("MIAA-784", requested)
        self.assertIn("MIAA-785", requested)
        self.assertIn("category:7", requested)
        self.assertIn("category:8", requested)
        self.assertIn("maker:11", requested)
        self.assertIn("series:12", requested)
        self.assertIn("label:13", requested)
        self.assertIn("actress:26225", requested)
        self.assertEqual(bulk_lookup.call_count, 1)
        self.assertEqual(result[0]["title_ja_translated"], "标题A")
        self.assertEqual(result[0]["categories"][0]["name_ja_translated"], "痴女中文")
        self.assertEqual(result[0]["maker"]["name_ja_translated"], "片商")
        self.assertEqual(result[0]["series"]["name_translated"], "系列")
        self.assertEqual(result[0]["label"]["name_ja_translated"], "厂牌")
        self.assertEqual(result[0]["actresses"][0]["name_ja_translated"], "三上悠亚")
        self.assertEqual(result[1]["title_ja_translated"], "标题B")
        self.assertEqual(result[1]["categories"][0]["name_ja_translated"], "企划")

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

    async def test_translate_supplement_sources_can_use_local_mappings_only(self):
        from database import upsert_cached_translation
        from translations.providers import AIProvider

        service = self.service()
        upsert_cached_translation(
            "supplement:summary:Original summary",
            "Original summary",
            "已有简介",
            "ai",
            "test-model",
        )
        data = {
            "chosen_fields": [
                {"field_name": "summary", "field_value": "Original summary"},
                {"field_name": "maker_name", "field_value": "LEO"},
            ],
        }

        with patch.object(AIProvider, "translate", new_callable=AsyncMock) as ai_translate:
            translated = await service.translate_supplement_sources(data, allow_network=False)

        self.assertEqual(translated["chosen_fields"][0]["field_value_translated"], "已有简介")
        self.assertNotIn("field_value_translated", translated["chosen_fields"][1])
        ai_translate.assert_not_awaited()

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

    async def test_selected_provider_uses_only_one_network_source(self):
        from translations.providers import BaiduTranslateProvider, GoogleFreeProvider, TranslationResult

        service = self.service()
        service.settings["baidu"] = {"enabled": True, "app_id": "appid", "secret": "secret"}
        with patch.object(
            BaiduTranslateProvider,
            "translate",
            AsyncMock(return_value=TranslationResult("百度译文", "baidu")),
        ) as baidu_translate, patch.object(GoogleFreeProvider, "translate", new_callable=AsyncMock) as google_translate:
            translated = await service.translate_text(
                "原文",
                scope="title:MIAA-784:title_ja",
                provider_order=["cache", "mapping", "baidu", "google_free"],
                return_original=False,
            )

        self.assertEqual(translated, "百度译文")
        baidu_translate.assert_awaited_once()
        google_translate.assert_not_awaited()

    async def test_baidu_translate_signs_request_and_maps_language(self):
        from translations.providers import BaiduTranslateProvider, TranslationRequest

        captured = {}

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"trans_result": [{"src": "テスト", "dst": "测试"}]}

        async def fake_post(self, url, data=None):
            captured["url"] = url
            captured["data"] = data
            return Response()

        provider = BaiduTranslateProvider({
            "enabled": True,
            "app_id": "appid",
            "secret": "secret",
            "endpoint": "https://example.test/translate",
            "timeout": 3,
        })
        request = TranslationRequest(text="テスト", scope="title:1", target_language="zh-CN", source_language="ja")

        with patch("httpx.AsyncClient.post", new=fake_post), patch("translations.providers._salt", return_value="12345"):
            result = await provider.translate(request)

        self.assertEqual(result.translated_text, "测试")
        self.assertEqual(result.provider, "baidu")
        self.assertEqual(captured["url"], "https://example.test/translate")
        data = captured["data"]
        self.assertEqual(data["q"], "テスト")
        self.assertEqual(data["from"], "jp")
        self.assertEqual(data["to"], "zh")
        self.assertEqual(data["salt"], "12345")
        self.assertEqual(data["sign"], "4f3b0ccd7300b2305137b9ada4a1765b")

    async def test_baidu_translate_many_splits_matching_lines(self):
        from translations.providers import BaiduTranslateProvider, TranslationRequest

        captured = {}

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"trans_result": [{"src": "一\n二", "dst": "one\ntwo"}]}

        async def fake_post(self, url, data=None):
            captured["data"] = data
            return Response()

        provider = BaiduTranslateProvider({"enabled": True, "app_id": "appid", "secret": "secret", "qps": 0})
        requests = [
            TranslationRequest(text="一", scope="category:1", target_language="zh-CN"),
            TranslationRequest(text="二", scope="category:2", target_language="zh-CN"),
        ]

        with patch("httpx.AsyncClient.post", new=fake_post):
            results = await provider.translate_many(requests)

        self.assertEqual([result.translated_text for result in results], ["one", "two"])
        self.assertEqual(captured["data"]["q"], "一\n二")

    async def test_baidu_translate_returns_none_for_api_error(self):
        from translations.providers import BaiduTranslateProvider, TranslationRequest

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"error_code": "54003", "error_msg": "Invalid Access Limit"}

        async def fake_post(self, url, data=None):
            return Response()

        provider = BaiduTranslateProvider({"enabled": True, "app_id": "appid", "secret": "secret"})

        with patch("httpx.AsyncClient.post", new=fake_post):
            result = await provider.translate(TranslationRequest(text="一", scope="category:1"))

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
