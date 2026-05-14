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
             patch.object(GoogleFreeProvider, "translate", AsyncMock(return_value=TranslationResult("测试标题", "google_free"))), \
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

        async def translate(request):
            return TranslationResult(f"{request.text}中文", "google_free")

        job_id = add_translation_job("metadata_makers", provider_order=["cache", "google_free"])

        with patch("translations.jobs.get_info_client", return_value=Client()), \
             patch.object(GoogleFreeProvider, "translate", AsyncMock(side_effect=translate)), \
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


if __name__ == "__main__":
    unittest.main()
