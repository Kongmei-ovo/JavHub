from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from fastapi.routing import APIRoute
from routers import videos
from routers.videos import router, search_videos
from test_support.client import create_router_test_client
from test_support.cache import FakeRedisMixin
from test_support.translations import passthrough_video_translator


def _search_kwargs(**overrides):
    params = {
        "q": None,
        "content_id": None,
        "dvd_id": None,
        "maker_id": None,
        "maker_name": None,
        "series_id": None,
        "series_name": None,
        "actress_id": None,
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
        "random": None,
        "include_total": None,
        "variant_mode": "grouped",
        "variant_scope": "page",
        "include_variant_explanations": True,
        "include_search_diagnostics": False,
        "preferred_actresses": None,
        "preferred_makers": None,
        "preferred_series": None,
        "preferred_categories": None,
        "page": 1,
        "page_size": 20,
    }
    params.update(overrides)
    return params


class VideosMetadataRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

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
        translator.translate_videos.return_value = [{"content_id": "miaa784", "title_ja": "原文"}]

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
            "variant_mode": "grouped",
            "variant_scope": "page",
            "include_variant_explanations": True,
            "page": 1,
            "page_size": 30,
        }

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            data = await search_videos(**kwargs)

        self.assertEqual(data["total_count"], 1)
        translator.translate_videos.assert_awaited_once()
        self.assertFalse(translator.translate_videos.await_args.kwargs["allow_network"])
        self.assertEqual(data["data"][0]["variant_group_count"], 1)

    async def test_search_route_injects_variant_metadata_and_cache_key_includes_mode(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                    {"content_id": "miaa00784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title （BOD）", "service_code": "mono"},
                ],
                "total_count": 2,
                "total_pages": 1,
            },
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                    {"content_id": "miaa00784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title （BOD）", "service_code": "mono"},
                ],
                "total_count": 2,
                "total_pages": 1,
            },
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            grouped = await search_videos(**_search_kwargs(q="miaa", variant_mode="grouped", include_variant_explanations=True))
            flat = await search_videos(**_search_kwargs(q="miaa", variant_mode="flat", include_variant_explanations=True))

        self.assertEqual(len(grouped["data"]), 1)
        self.assertEqual(grouped["data"][0]["variant_group_count"], 2)
        self.assertIn("BOD 蓝光按需", [label["label"] for label in grouped["data"][0]["variant_group_items"][1]["variant_labels"]])
        self.assertEqual(len(flat["data"]), 2)
        self.assertEqual(client.search_videos.await_count, 2)

    async def test_search_route_indexed_scope_uses_index_and_cache_key_includes_scope(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital"},
                ],
                "total_count": 1,
                "total_pages": 1,
            },
            {
                "data": [
                    {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital"},
                ],
                "total_count": 1,
                "total_pages": 1,
            },
        ]
        translator = passthrough_video_translator()

        def apply_index(items, **_kwargs):
            row = dict(items[0])
            row["variant_indexed"] = True
            row["variant_group_count"] = 5
            row["variant_group_items"] = [{"content_id": "miaa00784", "display_code": "MIAA-784"}]
            return [row]

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator), \
             patch("routers.videos.apply_indexed_variant_groups", side_effect=apply_index) as indexed:
            indexed_result = await search_videos(**_search_kwargs(q="miaa", variant_scope="indexed"))
            page_result = await search_videos(**_search_kwargs(q="miaa", variant_scope="page"))

        self.assertTrue(indexed_result["data"][0]["variant_indexed"])
        self.assertEqual(indexed_result["data"][0]["variant_group_count"], 5)
        self.assertFalse(page_result["data"][0].get("variant_indexed", False))
        indexed.assert_called_once()
        self.assertEqual(client.search_videos.await_count, 2)

    async def test_search_route_expands_exact_code_result_with_safe_variant_lookups(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [
                {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
            ],
            "total_count": 1,
            "total_pages": 1,
        }
        client.batch_lookup_by_dvd_id.return_value = {
            "TKMIAA-784": {"content_id": "tkmiaa784", "dvd_id": "TKMIAA-784", "title_ja": "【FANZA限定】Title 生写真3枚付き", "service_code": "mono"},
            "MIAA-784BOD": {"content_id": "miaa784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title （BOD）", "service_code": "mono"},
            "4MIAA784": {"content_id": "4miaa784", "dvd_id": "4MIAA784", "title_ja": "Title", "service_code": "rental"},
        }
        client.batch_get_videos.return_value = [
            {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital"},
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(
                **_search_kwargs(
                    content_id="MIAA-784",
                    variant_mode="grouped",
                    include_variant_explanations=True,
                )
            )

        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["variant_group_count"], 5)
        labels = [
            label["label"]
            for item in result["data"][0]["variant_group_items"]
            for label in item.get("variant_labels", [])
        ]
        self.assertIn("FANZA限定特典", labels)
        self.assertIn("BOD 蓝光按需", labels)
        self.assertIn("租赁版", labels)
        self.assertIn("数字版", labels)
        client.search_videos.assert_awaited_once()
        client.batch_lookup_by_dvd_id.assert_awaited_once_with([
            "TKMIAA-784",
            "MIAA-784BOD",
            "MIAA-784DOD",
            "MIAA-784RDOD",
            "4MIAA784",
        ])
        client.batch_get_videos.assert_awaited_once_with(["miaa00784"])

    async def test_search_route_keeps_base_result_when_variant_batch_lookup_fails(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [
                {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
            ],
            "total_count": 1,
            "total_pages": 1,
        }
        client.batch_lookup_by_dvd_id.side_effect = RuntimeError("lookup unavailable")
        client.batch_get_videos.side_effect = RuntimeError("batch unavailable")
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(
                **_search_kwargs(
                    content_id="MIAA-784",
                    variant_mode="grouped",
                    include_variant_explanations=True,
                )
            )

        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["display_code"], "MIAA-784")
        self.assertEqual(result["data"][0]["variant_group_count"], 1)
        client.search_videos.assert_awaited_once()

    async def test_search_route_forwards_include_total_when_provided(self):
        client = AsyncMock()
        client.search_videos.return_value = {"data": [], "total_count": -1, "total_pages": -1}

        with patch("routers.videos.get_info_client", return_value=client):
            result = await search_videos(**_search_kwargs(include_total=False))

        self.assertEqual(result["total_count"], -1)
        self.assertFalse(client.search_videos.await_args.kwargs["include_total"])

    async def test_search_route_understands_code_and_remaining_keywords_from_free_text(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [{"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "制服作品"}],
            "total_count": 1,
            "total_pages": 1,
        }
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="miaa 784 制服"))

        self.assertEqual(result["data"][0]["display_code"], "MIAA-784")
        client.search_videos.assert_awaited_once()
        self.assertEqual(client.search_videos.await_args.kwargs["content_id"], "MIAA-784")
        self.assertEqual(client.search_videos.await_args.kwargs["q"], "制服")

    async def test_search_route_expands_free_text_into_metadata_recall_and_reranks_matches(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("q") == "yotsuha moodyz cosplay":
                return {
                    "data": [
                        {
                            "content_id": "weak-title",
                            "dvd_id": "WTA-001",
                            "title_ja": "Yotsuha Cosplay Mention",
                            "maker_name": "Other",
                            "release_date": "2021-01-01",
                        }
                    ],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("actress_name") == "小湊よつ葉":
                return {
                    "data": [
                        {
                            "content_id": "actor-hit",
                            "dvd_id": "MIAA-101",
                            "title_ja": "演员命中",
                            "actress_name": "小湊よつ葉",
                            "release_date": "2024-03-01",
                        }
                    ],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("maker_name") == "MOODYZ":
                return {
                    "data": [
                        {
                            "content_id": "maker-hit",
                            "dvd_id": "MIAA-102",
                            "title_ja": "厂商命中",
                            "maker_name": "MOODYZ",
                            "release_date": "2024-02-01",
                        }
                    ],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("category_name") == "コスプレ":
                return {
                    "data": [
                        {
                            "content_id": "tag-hit",
                            "dvd_id": "MIAA-103",
                            "title_ja": "题材命中",
                            "categories": [{"name_ja": "コスプレ"}],
                            "release_date": "2024-01-01",
                        }
                    ],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("year") == 2024:
                return {
                    "data": [
                        {
                            "content_id": "maker-hit",
                            "dvd_id": "MIAA-102",
                            "title_ja": "厂商命中",
                            "maker_name": "MOODYZ",
                            "release_date": "2024-02-01",
                        }
                    ],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {
            "data": [{"id": 26225, "actress_name": "小湊よつ葉", "name_romaji": "Yotsuha Kominato"}]
        }
        client.list_makers.return_value = [{"id": 1, "name": "MOODYZ", "name_ja": "MOODYZ"}]
        client.list_series.return_value = []
        client.list_categories.return_value = [{"id": 5023, "name_ja": "コスプレ", "name_en": "Cosplay"}]
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="yotsuha moodyz cosplay 2024", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], [
            "actor-hit",
            "maker-hit",
            "tag-hit",
            "weak-title",
        ])
        self.assertEqual(result["total_count"], 4)
        calls = [call.kwargs for call in client.search_videos.await_args_list]
        self.assertIn({"q": "yotsuha moodyz cosplay", "content_id": None, "dvd_id": None}, [
            {key: kwargs.get(key) for key in ("q", "content_id", "dvd_id")}
            for kwargs in calls
        ])
        self.assertIn("小湊よつ葉", [kwargs.get("actress_name") for kwargs in calls])
        self.assertIn("MOODYZ", [kwargs.get("maker_name") for kwargs in calls])
        self.assertIn("コスプレ", [kwargs.get("category_name") for kwargs in calls])
        self.assertIn(2024, [kwargs.get("year") for kwargs in calls])

    async def test_search_route_applies_history_preference_hints_as_lightweight_ranking(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [
                {
                    "content_id": "plain",
                    "dvd_id": "AAA-001",
                    "title_ja": "普通结果",
                    "actress_name": "其他演员",
                    "maker_name": "Other",
                    "release_date": "2024-04-01",
                },
                {
                    "content_id": "preferred",
                    "dvd_id": "MIAA-101",
                    "title_ja": "偏好结果",
                    "actress_name": "小湊よつ葉",
                    "maker_name": "MOODYZ",
                    "release_date": "2024-01-01",
                },
            ],
            "total_count": 2,
            "total_pages": 1,
        }
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(
                **_search_kwargs(
                    q="制服",
                    preferred_actresses="小湊よつ葉",
                    preferred_makers="MOODYZ",
                )
            )

        self.assertEqual([item["content_id"] for item in result["data"]], ["preferred", "plain"])
        client.search_videos.assert_awaited_once()
        self.assertNotIn("preferred_actresses", client.search_videos.await_args.kwargs)

    async def test_search_route_tolerates_typoed_alias_tokens_in_metadata_recall(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("actress_name") == "小湊よつ葉":
                return {
                    "data": [{"content_id": "actor-hit", "dvd_id": "MIAA-101", "actress_name": "小湊よつ葉"}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("maker_name") == "MOODYZ":
                return {
                    "data": [{"content_id": "maker-hit", "dvd_id": "MIAA-102", "maker_name": "MOODYZ"}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("category_name") == "コスプレ":
                return {
                    "data": [{"content_id": "tag-hit", "dvd_id": "MIAA-103", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {
            "data": [{"id": 26225, "actress_name": "小湊よつ葉", "name_romaji": "Yotsuha Kominato"}]
        }
        client.list_makers.return_value = [{"id": 1, "name": "MOODYZ"}]
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="yotuha moodyz cosply 2024", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], [
            "actor-hit",
            "maker-hit",
            "tag-hit",
        ])

    async def test_search_route_matches_compact_initial_and_consonant_tokens_in_metadata_recall(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("actress_name") == "小湊よつ葉":
                return {
                    "data": [{"content_id": "actor-hit", "dvd_id": "MIAA-101", "actress_name": "小湊よつ葉"}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("maker_name") == "MOODYZ":
                return {
                    "data": [{"content_id": "maker-hit", "dvd_id": "MIAA-102", "maker_name": "MOODYZ"}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if kwargs.get("category_name") == "コスプレ":
                return {
                    "data": [{"content_id": "tag-hit", "dvd_id": "MIAA-103", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {
            "data": [{"id": 26225, "actress_name": "小湊よつ葉", "name_romaji": "Yotsuha Kominato"}]
        }
        client.list_makers.return_value = [{"id": 1, "name": "MOODYZ"}]
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="yk mdz cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], [
            "actor-hit",
            "maker-hit",
            "tag-hit",
        ])

    async def test_search_route_supports_compact_field_operators_and_year_ranges(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [{"content_id": "structured-hit", "dvd_id": "MIAA-201"}],
            "total_count": 1,
            "total_pages": 1,
        }
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="actor:yotsuha maker:moodyz tag:cosplay 2024..2026"))

        self.assertEqual(result["data"][0]["content_id"], "structured-hit")
        client.search_videos.assert_awaited_once()
        kwargs = client.search_videos.await_args.kwargs
        self.assertIsNone(kwargs["q"])
        self.assertEqual(kwargs["actress_name"], "yotsuha")
        self.assertEqual(kwargs["maker_name"], "moodyz")
        self.assertEqual(kwargs["category_name"], "コスプレ")
        self.assertEqual(kwargs["year_from"], 2024)
        self.assertEqual(kwargs["year_to"], 2026)

    async def test_search_route_can_return_search_diagnostics_for_recall_budget(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("category_name") == "コスプレ":
                return {
                    "data": [{"content_id": "tag-hit", "dvd_id": "MIAA-103", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="cosplay 2024", include_search_diagnostics=True))

        diagnostics = result["search_diagnostics"]
        self.assertTrue(diagnostics["metadata_recall"])
        self.assertIn("category_name", diagnostics["recall_fields"])
        self.assertIn("コスプレ", diagnostics["semantic_categories"])
        self.assertLessEqual(diagnostics["recall_request_count"], diagnostics["recall_request_limit"])

    async def test_search_route_understands_season_words_as_release_date_ranges(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if (
                kwargs.get("category_name") == "コスプレ"
                and kwargs.get("release_date_from") == "2024-03-01"
                and kwargs.get("release_date_to") == "2024-05-31"
            ):
                return {
                    "data": [{"content_id": "spring-hit", "dvd_id": "MIAA-301", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="spring 2024 cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], ["spring-hit"])

    async def test_search_route_expands_multiple_semantic_category_aliases(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            category_name = kwargs.get("category_name")
            if category_name == "メイド":
                return {
                    "data": [{"content_id": "maid-hit", "dvd_id": "MIAA-401", "categories": [{"name_ja": "メイド"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if category_name == "水着":
                return {
                    "data": [{"content_id": "swimsuit-hit", "dvd_id": "MIAA-402", "categories": [{"name_ja": "水着"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            if category_name == "アイドル":
                return {
                    "data": [{"content_id": "idol-hit", "dvd_id": "MIAA-403", "categories": [{"name_ja": "アイドル"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="maid swimsuit idol 2024", include_search_diagnostics=True))

        self.assertEqual([item["content_id"] for item in result["data"]], [
            "maid-hit",
            "swimsuit-hit",
            "idol-hit",
        ])
        self.assertEqual(result["search_diagnostics"]["semantic_categories"], ["メイド", "水着", "アイドル"])

    async def test_search_route_understands_recency_sort_words(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [{"content_id": "latest-hit", "dvd_id": "MIAA-501"}],
            "total_count": 1,
            "total_pages": 1,
        }
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="latest"))

        self.assertEqual(result["data"][0]["content_id"], "latest-hit")
        client.search_videos.assert_awaited_once()
        kwargs = client.search_videos.await_args.kwargs
        self.assertIsNone(kwargs["q"])
        self.assertEqual(kwargs["sort_by"], "release_date")
        self.assertEqual(kwargs["sort_order"], "desc")

    async def test_search_route_understands_quarter_words_as_release_date_ranges(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if (
                kwargs.get("category_name") == "コスプレ"
                and kwargs.get("release_date_from") == "2024-04-01"
                and kwargs.get("release_date_to") == "2024-06-30"
            ):
                return {
                    "data": [{"content_id": "quarter-hit", "dvd_id": "MIAA-601", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="q2 2024 cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], ["quarter-hit"])

    async def test_search_route_understands_chinese_relative_year_words(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("category_name") == "コスプレ" and kwargs.get("year") == 2025:
                return {
                    "data": [{"content_id": "last-year-hit", "dvd_id": "MIAA-701", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator), \
             patch("routers.videos._current_year", return_value=2026, create=True):
            result = await search_videos(**_search_kwargs(q="去年 cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], ["last-year-hit"])

    async def test_search_route_normalizes_full_width_pasted_code_tokens(self):
        client = AsyncMock()
        client.search_videos.return_value = {
            "data": [{"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "命中"}],
            "total_count": 1,
            "total_pages": 1,
        }
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="ＭＩＡＡ＿７８４ 制服"))

        self.assertEqual(result["data"][0]["content_id"], "miaa784")
        kwargs = client.search_videos.await_args.kwargs
        self.assertEqual(kwargs["content_id"], "MIAA-784")
        self.assertEqual(kwargs["q"], "制服")

    async def test_search_route_understands_year_month_as_release_date_range(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if (
                kwargs.get("category_name") == "コスプレ"
                and kwargs.get("release_date_from") == "2024-05-01"
                and kwargs.get("release_date_to") == "2024-05-31"
            ):
                return {
                    "data": [{"content_id": "month-hit", "dvd_id": "MIAA-801", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="2024-05 cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], ["month-hit"])

    async def test_search_route_understands_oldest_sort_words(self):
        client = AsyncMock()

        async def fake_search(**kwargs):
            if kwargs.get("category_name") == "コスプレ" and kwargs.get("sort_order") == "asc":
                return {
                    "data": [{"content_id": "oldest-hit", "dvd_id": "MIAA-901", "categories": [{"name_ja": "コスプレ"}]}],
                    "total_count": 1,
                    "total_pages": 1,
                }
            return {"data": [], "total_count": 0, "total_pages": 0}

        client.search_videos.side_effect = fake_search
        client.list_actresses.return_value = {"data": []}
        client.list_makers.return_value = []
        client.list_series.return_value = []
        client.list_categories.return_value = []
        client.list_labels.return_value = []
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            result = await search_videos(**_search_kwargs(q="oldest cosplay", include_total=True))

        self.assertEqual([item["content_id"] for item in result["data"]], ["oldest-hit"])

    async def test_search_route_caches_translated_response_for_non_random_requests(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {"data": [{"content_id": "miaa784", "title_ja": "原文"}], "total_count": -1, "total_pages": -1},
            {"data": [{"content_id": "miaa785", "title_ja": "別版"}], "total_count": -1, "total_pages": -1},
        ]
        translator = AsyncMock()
        translator.translate_videos.side_effect = [
            [{"content_id": "miaa784", "title_ja": "译文"}],
            [{"content_id": "miaa785", "title_ja": "別版译文"}],
        ]

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            first = await search_videos(**_search_kwargs(q="abc", include_total=False))
            second = await search_videos(**_search_kwargs(q="abc", include_total=False))
            other_page = await search_videos(**_search_kwargs(q="abc", include_total=False, page=2))

        self.assertEqual(second, first)
        self.assertEqual(other_page["data"][0]["content_id"], "miaa785")
        self.assertEqual(client.search_videos.await_count, 2)
        self.assertEqual(translator.translate_videos.await_count, 2)

    def test_search_cache_zero_bypasses_cached_response(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {"data": [{"content_id": "old", "title_ja": "旧"}], "total_count": -1, "total_pages": -1},
            {"data": [{"content_id": "fresh", "title_ja": "新"}], "total_count": -1, "total_pages": -1},
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            http = create_router_test_client(videos.router)
            first = http.get("/api/v1/videos/search?q=abc&include_total=false")
            cached = http.get("/api/v1/videos/search?q=abc&include_total=false")
            fresh = http.get("/api/v1/videos/search?q=abc&include_total=false&cache=0")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(first.json()["data"][0]["content_id"], "old")
        self.assertEqual(cached.json()["data"][0]["content_id"], "old")
        self.assertEqual(fresh.json()["data"][0]["content_id"], "fresh")
        self.assertEqual(client.search_videos.await_count, 2)

    async def test_search_route_does_not_cache_random_requests_when_total_is_required(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {"data": [{"content_id": "first"}], "total_count": 2, "total_pages": 1},
            {"data": [{"content_id": "second"}], "total_count": 2, "total_pages": 1},
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            first = await search_videos(**_search_kwargs(random="1", include_total=True))
            second = await search_videos(**_search_kwargs(random="1", include_total=True))

        self.assertEqual(first["data"][0]["content_id"], "first")
        self.assertEqual(second["data"][0]["content_id"], "second")
        self.assertEqual(client.search_videos.await_count, 2)
        self.assertEqual(translator.translate_videos.await_count, 2)

    async def test_random_search_with_no_total_uses_short_response_cache(self):
        client = AsyncMock()
        client.search_videos.side_effect = [
            {"data": [{"content_id": "first"}], "total_count": -1, "total_pages": -1},
            {"data": [{"content_id": "second"}], "total_count": -1, "total_pages": -1},
            {"data": [{"content_id": "third"}], "total_count": -1, "total_pages": -1},
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            first = await search_videos(**_search_kwargs(random="1", include_total=False))
            second = await search_videos(**_search_kwargs(random="1", include_total=False))
            other_page = await search_videos(**_search_kwargs(random="1", include_total=False, page=2))

        self.assertEqual(second, first)
        self.assertEqual(other_page["data"][0]["content_id"], "second")
        self.assertEqual(client.search_videos.await_count, 2)
        self.assertEqual(translator.translate_videos.await_count, 2)

    async def test_list_videos_defaults_to_no_total_and_caches_translated_response(self):
        client = AsyncMock()
        client.list_videos.return_value = {
            "data": [{"content_id": "miaa784", "title_ja": "原文"}],
            "total_count": -1,
            "total_pages": -1,
        }
        translator = AsyncMock()
        translator.translate_videos.return_value = [{"content_id": "miaa784", "title_ja": "译文"}]

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            first = await videos.list_videos(page=1, page_size=20)
            second = await videos.list_videos(page=1, page_size=20)

        self.assertEqual(first, second)
        self.assertEqual(first["total_count"], -1)
        client.list_videos.assert_awaited_once_with(page=1, page_size=20, include_total=False)
        translator.translate_videos.assert_awaited_once()

    async def test_list_videos_cache_key_includes_include_total(self):
        client = AsyncMock()
        client.list_videos.side_effect = [
            {"data": [{"content_id": "no-total"}], "total_count": -1, "total_pages": -1},
            {"data": [{"content_id": "with-total"}], "total_count": 100, "total_pages": 5},
        ]
        translator = passthrough_video_translator()

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            no_total = await videos.list_videos(page=1, page_size=20, include_total=False)
            with_total = await videos.list_videos(page=1, page_size=20, include_total=True)

        self.assertEqual(no_total["total_count"], -1)
        self.assertEqual(with_total["total_count"], 100)
        self.assertEqual(client.list_videos.await_count, 2)
        self.assertEqual(translator.translate_videos.await_count, 2)

    async def test_get_video_caches_translated_detail_by_content_and_service(self):
        client = AsyncMock()
        client.get_video.side_effect = [
            {"content_id": "MIAA-784", "title_ja": "原文"},
            {"content_id": "MIAA-784", "title_ja": "別版"},
        ]
        translator = AsyncMock()
        translator.translate_video.side_effect = [
            {"content_id": "MIAA-784", "title_ja": "译文"},
            {"content_id": "MIAA-784", "title_ja": "別版译文"},
        ]

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            first = await videos.get_video("MIAA-784", service_code="digital")
            second = await videos.get_video("miaa784", service_code="digital")
            other_service = await videos.get_video("miaa784", service_code="mono")

        self.assertEqual(second, first)
        self.assertEqual(other_service["title_ja"], "別版译文")
        self.assertEqual(client.get_video.await_count, 2)
        self.assertEqual(translator.translate_video.await_count, 2)

    async def test_get_video_uses_cache_only_translation_for_foreground_detail(self):
        client = AsyncMock()
        client.get_video.return_value = {"content_id": "MIAA-784", "title_ja": "原文", "summary": "简介"}
        translator = AsyncMock()
        translator.translate_video.return_value = {"content_id": "MIAA-784", "title_ja": "译文"}

        with patch("routers.videos.get_info_client", return_value=client), \
             patch("routers.videos.get_translator_service", return_value=translator):
            await videos.get_video("MIAA-784")

        translator.translate_video.assert_awaited_once()
        self.assertFalse(translator.translate_video.await_args.kwargs["allow_network"])

    async def test_translation_test_route_uses_selected_provider_order(self):
        from routers.translation import test_translation

        class Translator:
            def __init__(self):
                self.settings = {"provider_order": ["cache", "mapping", "openai_compatible"]}
                self.seen_order = None

            async def translate_text(self, *args, **kwargs):
                self.seen_order = list(kwargs["provider_order"])
                return "译文"

        translator = Translator()
        with patch("routers.translation.get_translator_service", return_value=translator):
            result = await test_translation({"text": "原文"})

        self.assertEqual(result["translated_text"], "译文")
        self.assertEqual(translator.seen_order, ["cache", "mapping", "google_free"])
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
