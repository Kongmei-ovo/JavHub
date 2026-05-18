from __future__ import annotations

import asyncio
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


class TranslationJobsTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_title_stats_ignore_legacy_empty_string_title_json(self):
        from database import get_all_translations, get_db, get_translation_count, upsert_translation

        upsert_translation("actress:100", {"actress": {"名前": "名字"}})
        upsert_translation("MIAA-784", {"title": {"テストタイトル": "测试标题"}})
        with get_db() as conn:
            conn.execute(
                "INSERT INTO translation_mappings (content_id, title_json) VALUES (?, ?)",
                ("legacy-empty-title", '""'),
            )

        self.assertEqual(get_translation_count("title"), 1)
        self.assertEqual(get_all_translations("title"), {"MIAA-784": {"テストタイトル": "测试标题"}})

    async def test_non_title_mapping_keeps_empty_title_object(self):
        from database import get_db, get_translation_count, upsert_translation

        upsert_translation("category:2024", {"category": {"ドラマ": "剧情"}})

        with get_db() as conn:
            row = conn.execute(
                "SELECT title_json FROM translation_mappings WHERE content_id = ?",
                ("category:2024",),
            ).fetchone()

        self.assertEqual(row["title_json"], "{}")
        self.assertEqual(get_translation_count("title"), 0)

    async def test_library_title_job_persists_title_mapping_without_ai(self):
        from database import get_translation
        from translations.jobs import _run_job
        from translations.providers import GoogleFreeProvider, OpenAICompatibleProvider, TranslationResult

        class Client:
            async def list_videos(self, page=1, page_size=20):
                return {
                    "data": [{"content_id": "MIAA-784", "title_ja": "テストタイトル"}],
                    "total_pages": 1,
                }

        from database import add_translation_job, get_translation_job
        job_id = add_translation_job("library_titles", provider_order=["cache", "google_free"])

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch.object(GoogleFreeProvider, "translate_many", AsyncMock(return_value=[TranslationResult("测试标题", "google_free")])), \
             patch.object(OpenAICompatibleProvider, "translate", new_callable=AsyncMock) as ai_translate:
            await _run_job(job_id, "library_titles", ["cache", "google_free"], limit=10, force=False)

        ai_translate.assert_not_awaited()
        job = get_translation_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["translated"], 1)
        self.assertEqual(job["total"], 1)
        self.assertEqual(job["progress_percent"], 100)
        self.assertEqual(job["provider_order"], ["cache", "google_free"])
        self.assertIsNotNone(job["started_at"])
        self.assertIsNotNone(job["finished_at"])
        self.assertIsNotNone(job["duration_seconds"])
        self.assertGreaterEqual(job["duration_seconds"], 0)
        self.assertEqual(job["result"]["provider_order"], ["cache", "google_free"])
        self.assertEqual(get_translation("miaa784")["title"]["テストタイトル"], "测试标题")

    async def test_library_title_job_can_use_ai_when_selected(self):
        from database import get_translation
        from translations.jobs import _run_job
        from translations.providers import AIProvider, GoogleFreeProvider, TranslationResult

        class Client:
            async def list_videos(self, page=1, page_size=20):
                return {
                    "data": [{"content_id": "MIAA-784", "title_ja": "テストタイトル"}],
                    "total_pages": 1,
                }

        from database import add_translation_job, get_translation_job
        job_id = add_translation_job("library_titles", provider_order=["cache", "mapping", "ai"])

        async def translate(request):
            self.assertEqual(request.context, "video title")
            return TranslationResult("AI测试标题", "ai", "test-model")

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch.object(AIProvider, "translate", AsyncMock(side_effect=translate)) as ai_translate, \
             patch.object(GoogleFreeProvider, "translate", new_callable=AsyncMock) as google_translate:
            await _run_job(job_id, "library_titles", ["cache", "mapping", "ai"], limit=10, force=False)

        ai_translate.assert_awaited_once()
        google_translate.assert_not_awaited()
        job = get_translation_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["translated"], 1)
        self.assertEqual(job["provider_order"], ["cache", "mapping", "ai"])
        self.assertEqual(get_translation("miaa784")["title"]["テストタイトル"], "AI测试标题")

    async def test_metadata_job_can_translate_only_makers(self):
        from database import add_translation_job, get_translation, get_translation_count
        from translations.jobs import _run_job
        from translations.providers import GoogleFreeProvider, OpenAICompatibleProvider, TranslationResult

        class Client:
            async def list_categories(self):
                raise AssertionError("metadata_makers should not collect categories")

            async def list_series(self):
                raise AssertionError("metadata_makers should not collect series")

            async def list_makers(self):
                return [{"id": 23, "name_ja": "テストメーカー"}]

            async def list_labels(self):
                raise AssertionError("metadata_makers should not collect labels")

            async def list_actresses(self, page=1, page_size=100):
                raise AssertionError("metadata_makers should not collect actresses")

        job_id = add_translation_job("metadata_makers", provider_order=["cache", "google_free"])

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch.object(
                 GoogleFreeProvider,
                 "translate_many",
                 AsyncMock(side_effect=lambda requests: [TranslationResult(f"{request.text}中文", "google_free") for request in requests]),
             ), \
             patch.object(OpenAICompatibleProvider, "translate", new_callable=AsyncMock) as ai_translate:
            await _run_job(job_id, "metadata_makers", ["cache", "google_free"], limit=10, force=False)

        ai_translate.assert_not_awaited()
        self.assertEqual(get_translation_count("maker"), 1)
        self.assertEqual(get_translation_count("category"), 0)
        self.assertEqual(get_translation("maker:23")["maker"]["テストメーカー"], "テストメーカー中文")

    async def test_metadata_actress_job_paginates_to_limit(self):
        from translations.jobs import _collect_metadata_names

        class Client:
            async def list_actresses(self, page=1, page_size=100):
                pages = {
                    1: [{"id": 1, "name_kanji": "一番"}, {"id": 2, "name_kanji": "二番"}],
                    2: [{"id": 3, "name_kanji": "三番"}],
                }
                return {"data": pages.get(page, []), "total_pages": 2, "total_count": 3}

        with patch("translations.jobs.get_info_client", return_value=Client()):
            rows = await _collect_metadata_names(("actress",), limit=3)

        self.assertEqual([row["id"] for row in rows], [1, 2, 3])
        self.assertEqual({row["type"] for row in rows}, {"actress"})

    async def test_metadata_names_limit_applies_per_field(self):
        from translations.jobs import _collect_metadata_names

        class Client:
            async def list_categories(self):
                return [
                    {"id": 10, "name_ja": "カテゴリ1"},
                    {"id": 11, "name_ja": "カテゴリ2"},
                    {"id": 12, "name_ja": "カテゴリ3"},
                ]

            async def list_series(self):
                return [
                    {"id": 20, "name_ja": "シリーズ1"},
                    {"id": 21, "name_ja": "シリーズ2"},
                    {"id": 22, "name_ja": "シリーズ3"},
                ]

            async def list_makers(self):
                return [{"id": 30, "name_ja": "メーカー"}]

            async def list_labels(self):
                return [{"id": 40, "name_ja": "レーベル"}]

            async def list_actresses(self, page=1, page_size=100):
                return {
                    "data": [{"id": 50, "name_kanji": "一番"}, {"id": 51, "name_kanji": "二番"}],
                    "total_pages": 1,
                }

        with patch("translations.jobs.get_info_client", return_value=Client()):
            rows = await _collect_metadata_names(limit=2)

        self.assertEqual(
            [row["type"] for row in rows],
            ["category", "category", "series", "series", "maker", "label", "actress", "actress"],
        )

    async def test_metadata_category_collection_decensors_masked_name_en(self):
        from translations.jobs import _collect_metadata_names

        class Client:
            async def list_categories(self):
                return [
                    {"id": 5064, "name_en": "H*******m"},
                    {"id": 4121, "name_en": "D***k Girl"},
                ]

        with patch("translations.jobs.get_info_client", return_value=Client()):
            rows = await _collect_metadata_names(("category",), limit=10)

        self.assertEqual(
            rows,
            [
                {"type": "category", "id": 5064, "text": "Hypnotism"},
                {"type": "category", "id": 4121, "text": "Drunk Girl"},
            ],
        )

    async def test_metadata_category_job_does_not_persist_masked_source_text(self):
        from database import add_translation_job, get_translation, get_translation_workbench_item
        from translations.jobs import _translate_metadata_names
        from translations.providers import GoogleFreeProvider, TranslationResult

        job_id = add_translation_job("metadata_categories", provider_order=["google_free"])
        counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
        items = [{"type": "category", "id": 5064, "text": "H*******m"}]

        async def translate_many(requests):
            self.assertEqual([request.text for request in requests], ["Hypnotism"])
            return [TranslationResult("催眠", "google_free")]

        with patch.object(GoogleFreeProvider, "translate_many", AsyncMock(side_effect=translate_many)):
            await _translate_metadata_names(job_id, items, ["google_free"], counters, force=False)

        self.assertEqual(get_translation("category:5064")["category"], {"Hypnotism": "催眠"})
        item = get_translation_workbench_item("category", 5064)
        self.assertEqual(item["source_text"], "Hypnotism")
        self.assertEqual(item["translated_text"], "催眠")
        self.assertNotIn("*", item["source_text"])

    async def test_repair_masked_category_translations_overwrites_machine_rows_only(self):
        from database import get_translation, get_translation_workbench_item, upsert_translation, upsert_translation_workbench_item
        from translations.category_decensor import repair_masked_category_translations

        upsert_translation("category:5064", {"category": {"H*******m": "高*****米"}})
        upsert_translation_workbench_item(
            "category",
            5064,
            "H*******m",
            translated_text="高*****米",
            status="machine_translated",
            provider="google_free",
        )
        upsert_translation("category:4058", {"category": {"ショタ": "正太"}})
        upsert_translation_workbench_item(
            "category",
            4058,
            "ショタ",
            translated_text="正太",
            status="manual_edited",
            provider="manual",
            preserve_reviewed=False,
        )

        repaired = repair_masked_category_translations()

        self.assertIn("5064", repaired)
        self.assertEqual(get_translation("category:5064")["category"], {"Hypnotism": "催眠"})
        repaired_item = get_translation_workbench_item("category", 5064)
        self.assertEqual(repaired_item["source_text"], "Hypnotism")
        self.assertEqual(repaired_item["translated_text"], "催眠")
        self.assertEqual(repaired_item["provider"], "decensor_repair")
        manual_item = get_translation_workbench_item("category", 4058)
        self.assertEqual(manual_item["source_text"], "ショタ")
        self.assertEqual(manual_item["translated_text"], "正太")
        self.assertEqual(manual_item["status"], "manual_edited")

    async def test_repair_masked_category_translations_is_noop_for_clean_database(self):
        from database import get_translation
        from translations.category_decensor import repair_masked_category_translations

        repaired = repair_masked_category_translations()

        self.assertEqual(repaired, [])
        self.assertIsNone(get_translation("category:5064"))

    async def test_init_db_repairs_legacy_masked_category_translations(self):
        from database import get_translation, get_translation_workbench_item, init_db, upsert_translation, upsert_translation_workbench_item

        upsert_translation("category:5064", {"category": {"H*******m": "高*****米"}})
        upsert_translation_workbench_item(
            "category",
            5064,
            "H*******m",
            translated_text="高*****米",
            status="machine_translated",
            provider="google_free",
        )

        init_db()

        self.assertEqual(get_translation("category:5064")["category"], {"Hypnotism": "催眠"})
        repaired_item = get_translation_workbench_item("category", 5064)
        self.assertEqual(repaired_item["source_text"], "Hypnotism")
        self.assertEqual(repaired_item["translated_text"], "催眠")
        self.assertEqual(repaired_item["provider"], "decensor_repair")

    async def test_repair_masked_category_translations_cleans_stale_key_without_overwriting_manual_item(self):
        from database import get_translation, get_translation_workbench_item, upsert_translation, upsert_translation_workbench_item
        from translations.category_decensor import repair_masked_category_translations

        upsert_translation("category:5064", {"category": {"H*******m": "高*****米", "Hypnotism": "人工催眠"}})
        upsert_translation_workbench_item(
            "category",
            5064,
            "Hypnotism",
            translated_text="人工催眠",
            status="manual_edited",
            provider="manual",
            preserve_reviewed=False,
        )

        repaired = repair_masked_category_translations()

        self.assertIn("5064", repaired)
        self.assertEqual(get_translation("category:5064")["category"], {"Hypnotism": "人工催眠"})
        manual_item = get_translation_workbench_item("category", 5064)
        self.assertEqual(manual_item["source_text"], "Hypnotism")
        self.assertEqual(manual_item["translated_text"], "人工催眠")
        self.assertEqual(manual_item["status"], "manual_edited")
        self.assertEqual(manual_item["provider"], "manual")

    async def test_title_job_uses_bounded_concurrency_and_keeps_failures_local(self):
        from database import add_translation_job, get_translation, get_translation_workbench_item, upsert_cached_translation, upsert_translation
        from translations.jobs import _translate_titles
        from translations.providers import GoogleFreeProvider, TranslationResult

        upsert_translation("skip001", {"title": {"既存": "已有"}})
        upsert_cached_translation("title:SKIP-002:title_ja", "缓存済み", "缓存译文", "google_free")

        items = [
            *[
                {"content_id": f"OK-{idx:03d}", "title_ja": f"タイトル{idx}"}
                for idx in range(10)
            ],
            {"content_id": "FAIL-001", "title_ja": "FAIL"},
            {"content_id": "SKIP-001", "title_ja": "既存"},
            {"content_id": "SKIP-002", "title_ja": "缓存済み"},
        ]
        active = 0
        max_active = 0

        async def translate_many(requests):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            try:
                await asyncio.sleep(0.01)
                return [
                    None if request.text == "FAIL" else TranslationResult(f"{request.text}中文", "google_free")
                    for request in requests
                ]
            finally:
                active -= 1

        job_id = add_translation_job("library_titles", provider_order=["google_free"])
        counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}

        with patch("translations.jobs._batch_concurrency", return_value=4), \
             patch("translations.jobs._batch_size", return_value=2), \
             patch("translations.jobs.logger.exception"), \
             patch.object(GoogleFreeProvider, "translate_many", AsyncMock(side_effect=translate_many)):
            await _translate_titles(job_id, items, ["google_free"], counters, force=False)

        self.assertGreater(max_active, 1)
        self.assertLessEqual(max_active, 4)
        self.assertEqual(counters, {"processed": 13, "translated": 11, "skipped": 1, "failed": 1})
        self.assertEqual(get_translation("ok000")["title"]["タイトル0"], "タイトル0中文")
        self.assertEqual(get_translation("skip002")["title"]["缓存済み"], "缓存済み中文")
        failed_item = get_translation_workbench_item("title", "FAIL-001")
        self.assertEqual(failed_item["status"], "failed")
        self.assertEqual(failed_item["attempts"], 1)

    async def test_title_job_counts_same_text_translation_as_done_without_cache_write(self):
        from database import add_translation_job, get_cached_translation, get_translation
        from translations.jobs import _translate_titles
        from translations.providers import GoogleFreeProvider, TranslationResult

        job_id = add_translation_job("library_titles", provider_order=["google_free"])
        counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
        items = [{"content_id": "MIAA-784", "title_ja": "MIAA-784"}]

        with patch.object(
            GoogleFreeProvider,
            "translate_many",
            AsyncMock(return_value=[TranslationResult("MIAA-784", "google_free")]),
        ):
            await _translate_titles(job_id, items, ["google_free"], counters, force=False)

        self.assertEqual(counters, {"processed": 1, "translated": 1, "skipped": 0, "failed": 0})
        self.assertEqual(get_translation("miaa784")["title"]["MIAA-784"], "MIAA-784")
        self.assertIsNone(get_cached_translation("title:MIAA-784:title_ja", "MIAA-784"))

    async def test_refresh_all_bypasses_cache_and_mapping_providers(self):
        from database import add_translation_job, get_translation, upsert_cached_translation, upsert_translation
        from translations.jobs import _translate_titles
        from translations.providers import GoogleFreeProvider, TranslationResult

        upsert_translation("miaa784", {"title": {"テストタイトル": "旧映射"}})
        upsert_cached_translation("title:MIAA-784:title_ja", "テストタイトル", "旧缓存", "google_free")

        job_id = add_translation_job("library_titles", provider_order=["cache", "mapping", "google_free"])
        counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}

        with patch.object(
            GoogleFreeProvider,
            "translate_many",
            AsyncMock(return_value=[TranslationResult("新译文", "google_free")]),
        ) as google_translate:
            await _translate_titles(
                job_id,
                [{"content_id": "MIAA-784", "title_ja": "テストタイトル"}],
                ["cache", "mapping", "google_free"],
                counters,
                force=True,
            )

        google_translate.assert_awaited_once()
        self.assertEqual(counters, {"processed": 1, "translated": 1, "skipped": 0, "failed": 0})
        self.assertEqual(get_translation("miaa784")["title"]["テストタイトル"], "新译文")

    async def test_job_retries_failed_workbench_items_before_page_scan(self):
        from database import add_translation_job, get_translation, get_translation_job, upsert_translation_workbench_item
        from translations.jobs import _run_job
        from translations.providers import GoogleFreeProvider, TranslationResult

        upsert_translation_workbench_item(
            "title",
            "FAIL-001",
            "失敗タイトル",
            status="failed",
            last_error="timeout",
        )

        class Client:
            async def list_videos(self, page=1, page_size=100):
                return {"data": [], "total_pages": 1, "total_count": 0}

        job_id = add_translation_job("library_titles", provider_order=["google_free"])

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch.object(
                 GoogleFreeProvider,
                 "translate_many",
                 AsyncMock(return_value=[TranslationResult("失败标题", "google_free")]),
             ):
            await _run_job(job_id, "library_titles", ["google_free"], force=False)

        job = get_translation_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["failed_retry_processed"], 1)
        self.assertEqual(get_translation("fail001")["title"]["失敗タイトル"], "失败标题")

    async def test_library_title_scan_groups_multiple_source_pages(self):
        from database import add_translation_job, get_translation_job
        from translations.jobs import _translate_library_titles_pages

        requested = []

        class Client:
            async def list_videos(self, page=1, page_size=100):
                requested.append((page, page_size))
                pages = {
                    1: [{"content_id": "AAA-001", "title_ja": "タイトル1"}, {"content_id": "AAA-002", "title_ja": "タイトル2"}],
                    2: [{"content_id": "AAA-003", "title_ja": "タイトル3"}, {"content_id": "AAA-004", "title_ja": "タイトル4"}],
                    3: [{"content_id": "AAA-005", "title_ja": "タイトル5"}],
                }
                return {"data": pages.get(page, []), "total_pages": 3, "total_count": 5}

        async def fake_translate(job_id, items, provider_order, counters, *, force, source_page=None):
            counters["processed"] += len(items)

        job_id = add_translation_job("library_titles", provider_order=["google_free"])
        counters = {"processed": 0, "translated": 0, "skipped": 0, "failed": 0}
        result_state = {}

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch("translations.jobs._source_page_size", return_value=2), \
             patch("translations.jobs._scan_pages_per_batch", return_value=2), \
             patch("translations.jobs._translate_titles", AsyncMock(side_effect=fake_translate)) as translate_titles:
            await _translate_library_titles_pages(
                job_id,
                ["google_free"],
                counters,
                force=False,
                result_state=result_state,
            )

        self.assertEqual(requested, [(1, 2), (2, 2), (3, 2)])
        self.assertEqual(translate_titles.await_count, 2)
        first_items = translate_titles.await_args_list[0].args[1]
        self.assertEqual([item["_source_page"] for item in first_items], [1, 1, 2, 2])
        self.assertEqual(counters["processed"], 5)
        job = get_translation_job(job_id)
        self.assertEqual(job["total"], 5)
        self.assertEqual(job["result"]["last_page"], 3)
        self.assertEqual(job["result"]["next_page"], 4)

    async def test_bulk_workbench_upsert_preserves_manual_rows_in_one_call(self):
        from database import (
            bulk_upsert_translation_workbench_items,
            get_translation_workbench_item,
            upsert_translation_workbench_item,
        )

        upsert_translation_workbench_item(
            "actress",
            26225,
            "三上悠亜",
            translated_text="三上悠亚",
            status="manual_edited",
            preserve_reviewed=False,
        )

        written = bulk_upsert_translation_workbench_items([
            {
                "item_type": "actress",
                "item_id": 26225,
                "source_text": "三上悠亜",
                "translated_text": "",
                "status": "untranslated",
                "provider": "mapping",
            }
        ])

        self.assertEqual(written, 1)
        item = get_translation_workbench_item("actress", 26225)
        self.assertEqual(item["status"], "manual_edited")
        self.assertEqual(item["translated_text"], "三上悠亚")

    async def test_pause_running_translation_job_marks_paused(self):
        from database import add_translation_job, get_translation_job
        from translations import jobs
        from translations.jobs import _run_job, pause_translation_job

        class Client:
            async def list_videos(self, page=1, page_size=100):
                await asyncio.sleep(10)
                return {"data": [], "total_pages": 1, "total_count": 0}

        job_id = add_translation_job("library_titles", provider_order=["google_free"])
        with patch("translations.jobs.get_info_client", return_value=Client()):
            task = asyncio.create_task(_run_job(job_id, "library_titles", ["google_free"], force=False))
            jobs._running_jobs[job_id] = task
            try:
                await asyncio.sleep(0.01)
                paused = pause_translation_job(job_id)
                self.assertIsNone(await task)
            finally:
                if job_id in jobs._running_jobs:
                    del jobs._running_jobs[job_id]
                jobs._paused_jobs.discard(job_id)

        self.assertEqual(paused["status"], "paused")
        self.assertEqual(get_translation_job(job_id)["status"], "paused")

    async def test_list_jobs_marks_orphaned_running_job_paused(self):
        from database import add_translation_job, get_translation_job, update_translation_job
        from translations.jobs import list_jobs

        job_id = add_translation_job("library_titles", provider_order=["google_free"])
        update_translation_job(job_id, status="running", result={"next_page": 42})

        jobs = list_jobs(limit=5)

        job = next(item for item in jobs if item["id"] == job_id)
        self.assertEqual(job["status"], "paused")
        self.assertFalse(job["running"])
        self.assertTrue(job["result"]["orphaned"])
        self.assertEqual(get_translation_job(job_id)["status"], "paused")


if __name__ == "__main__":
    unittest.main()
