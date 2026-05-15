from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from starlette.datastructures import UploadFile


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


async def _upload_json(payload: dict) -> UploadFile:
    return UploadFile(io.BytesIO(json.dumps(payload).encode("utf-8")), filename="translations.json")


async def _stream_json(response) -> dict:
    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8")
    return json.loads(body.decode("utf-8"))


class TranslationRouterTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_stats_coverage_uses_mappings_as_authoritative_and_reports_cache_separately(self):
        from database import upsert_cached_translation, upsert_translation
        from routers.translation import all_stats

        upsert_translation("MIAA-784", {"title": {"タイトル": "标题"}})
        upsert_cached_translation("title:miaa784:title_ja", "タイトル", "标题", "google_free")
        upsert_cached_translation("title:SSIS-001:title_ja", "別タイトル", "另一个标题", "google_free")
        upsert_translation("category:1", {"category": {"ドラマ": "剧情"}})
        upsert_cached_translation("category:2", "女優", "演员", "google_free")

        totals = {
            "/api/v1/videos": 3,
            "/api/v1/categories": 3,
            "/api/v1/actresses": 0,
            "/api/v1/series": 0,
            "/api/v1/makers": 0,
            "/api/v1/labels": 0,
        }

        class Client:
            async def get_total_count(self, path: str) -> int:
                return totals[path]

        with patch("routers.translation.get_info_client", return_value=Client()):
            stats = await all_stats()

        self.assertEqual(stats["coverage"]["title"], {
            "total": 3,
            "translated": 1,
            "untranslated": 2,
            "mapped": 1,
            "cached": 2,
        })
        self.assertEqual(stats["coverage"]["category"], {
            "total": 3,
            "translated": 1,
            "untranslated": 2,
        })

    async def test_import_accepts_self_describing_title_json_and_same_text_translation(self):
        from database import get_translation
        from routers.translation import import_trans

        payload = {
            "_type": "title",
            "_version": "2",
            "_src": "title_ja",
            "_dst": "title_translated",
            "data": {
                "MIAA-784": {
                    "content_id": "MIAA-784",
                    "title_ja": "MIAA-784",
                    "title_translated": "MIAA-784",
                }
            },
        }

        result = await import_trans("title", await _upload_json(payload))

        self.assertEqual(result["imported"], 1)
        self.assertEqual(get_translation("miaa784")["title"]["MIAA-784"], "MIAA-784")

    async def test_import_keeps_legacy_id_object_json(self):
        from database import get_translation
        from routers.translation import import_trans

        result = await import_trans(
            "category",
            await _upload_json({"7": {"name_ja": "ドラマ", "name_translated": "ドラマ"}}),
        )

        self.assertEqual(result["imported"], 1)
        self.assertEqual(get_translation("category:7")["category"]["ドラマ"], "ドラマ")

    async def test_export_uses_self_describing_json_wrapper(self):
        from database import upsert_translation
        from routers.translation import export_translations

        upsert_translation("miaa784", {"title": {"タイトル": "标题"}})

        payload = await _stream_json(await export_translations("title"))

        self.assertEqual(payload["_type"], "title")
        self.assertEqual(payload["_version"], "2")
        self.assertEqual(payload["_src"], "title_ja")
        self.assertEqual(payload["_dst"], "title_translated")
        self.assertEqual(payload["data"]["miaa784"]["title_ja"], "タイトル")
        self.assertEqual(payload["data"]["miaa784"]["title_translated"], "标题")

    async def test_start_job_uses_mode_without_limit_cap(self):
        from routers.translation import start_translation_job

        with patch(
            "routers.translation.create_translation_job",
            AsyncMock(return_value={"id": 5, "status": "pending"}),
        ) as create_job:
            result = await start_translation_job({
                "job_type": "library_titles",
                "provider_order": ["cache", "mapping", "google_free"],
                "mode": "refresh_all",
                "limit": 1,
            })

        self.assertEqual(result["id"], 5)
        create_job.assert_awaited_once_with(
            "library_titles",
            provider_order=["cache", "mapping", "google_free"],
            mode="refresh_all",
        )

    async def test_start_job_keeps_legacy_force_compatibility(self):
        from routers.translation import start_translation_job

        with patch(
            "routers.translation.create_translation_job",
            AsyncMock(return_value={"id": 6, "status": "pending"}),
        ) as create_job:
            await start_translation_job({"job_type": "metadata_names", "force": True})

        create_job.assert_awaited_once_with(
            "metadata_names",
            provider_order=None,
            mode="refresh_all",
        )

    async def test_workbench_manual_save_updates_mapping_and_history(self):
        from database import get_translation, upsert_translation_workbench_item
        from routers.translation import get_translation_item_history, list_translation_items, update_translation_item

        upsert_translation_workbench_item("actress", 26225, "三上悠亜")

        class Client:
            async def list_actresses(self, q=None, page=1, page_size=50):
                return {"data": [], "total_count": 0, "total_pages": 1}

        with patch("routers.translation.get_info_client", return_value=Client()):
            listed = await list_translation_items(item_type="actress", q="三上", page=1, page_size=20)
        self.assertEqual(listed["total_count"], 1)
        self.assertEqual(listed["data"][0]["status"], "untranslated")

        saved = await update_translation_item(
            "actress",
            "26225",
            {"action": "save", "source_text": "三上悠亜", "translated_text": "三上悠亚"},
        )

        self.assertEqual(saved["status"], "manual_edited")
        self.assertEqual(saved["translated_text"], "三上悠亚")
        self.assertEqual(get_translation("actress:26225")["actress"]["三上悠亜"], "三上悠亚")

        history = await get_translation_item_history("actress", "26225")
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(history["data"][0]["new_text"], "三上悠亚")

    async def test_workbench_list_sees_authoritative_mapping_rows(self):
        from database import upsert_translation
        from routers.translation import list_translation_items

        upsert_translation("actress:26225", {"actress": {"三上悠亜": "三上悠亚"}})

        class Client:
            async def list_actresses(self, q=None, page=1, page_size=50):
                return {"data": [], "total_count": 0, "total_pages": 1}

        with patch("routers.translation.get_info_client", return_value=Client()):
            listed = await list_translation_items(item_type="actress", q="三上悠亚", page=1, page_size=20)

        self.assertEqual(listed["total_count"], 1)
        self.assertEqual(listed["data"][0]["source_text"], "三上悠亜")
        self.assertEqual(listed["data"][0]["translated_text"], "三上悠亚")
        self.assertEqual(listed["data"][0]["provider"], "mapping")

    async def test_workbench_review_and_reset_status(self):
        from database import get_translation, upsert_translation_workbench_item, upsert_translation
        from routers.translation import update_translation_item

        upsert_translation("category:7", {"category": {"ドラマ": "剧情"}})
        upsert_translation_workbench_item(
            "category",
            7,
            "ドラマ",
            translated_text="剧情",
            status="machine_translated",
            provider="google_free",
        )

        reviewed = await update_translation_item("category", "7", {"action": "review"})
        self.assertEqual(reviewed["status"], "reviewed")

        reset = await update_translation_item("category", "7", {"action": "reset"})
        self.assertEqual(reset["status"], "untranslated")
        self.assertEqual(reset["translated_text"], "")
        self.assertFalse(get_translation("category:7")["category"].get("ドラマ"))

    async def test_retry_endpoint_creates_filtered_workbench_job(self):
        from routers.translation import retry_translation_items

        with patch(
            "routers.translation.create_translation_retry_job",
            AsyncMock(return_value={"id": 9, "status": "pending"}),
        ) as create_job:
            result = await retry_translation_items({
                "type": "actress",
                "status": "failed",
                "q": "三上",
                "ids": ["26225"],
                "provider_order": ["cache", "google_free"],
            })

        self.assertEqual(result["id"], 9)
        create_job.assert_awaited_once_with(
            item_type="actress",
            status="failed",
            q="三上",
            ids=["26225"],
            provider_order=["cache", "google_free"],
        )

    async def test_pause_job_endpoint_marks_job_paused(self):
        from routers.translation import pause_job

        with patch(
            "routers.translation.pause_translation_job",
            return_value={"id": 7, "status": "paused"},
        ) as pause:
            result = await pause_job(7)

        self.assertEqual(result["status"], "paused")
        pause.assert_called_once_with(7)


if __name__ == "__main__":
    unittest.main()
