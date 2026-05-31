from __future__ import annotations

import io
import json
import unittest
from unittest.mock import AsyncMock, patch

from starlette.datastructures import UploadFile

from test_support.postgres import TempPostgresMixin


async def _upload_json(payload: dict) -> UploadFile:
    return UploadFile(io.BytesIO(json.dumps(payload).encode("utf-8")), filename="translations.json")


async def _stream_json(response) -> dict:
    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8")
    return json.loads(body.decode("utf-8"))


def test_validate_mapping_type_rejects_unknown_with_stable_message():
    from fastapi import HTTPException
    from routers.translation import _validate_mapping_type

    self_describing_order = "actress, category, label, maker, series, title"
    assert _validate_mapping_type("title") == "title"

    try:
        _validate_mapping_type("bad")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == f"type must be one of: {self_describing_order}"
    else:
        raise AssertionError("invalid translation type should be rejected")


class TranslationRouterTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_all_stats_uses_short_response_cache(self):
        from database import upsert_translation
        from services import cache
        from routers.translation import all_stats

        upsert_translation("category:1", {"category": {"ドラマ": "剧情"}})
        total_calls = 0
        captured_ttl = None
        original_get_or_set = cache.get_or_set_response

        async def capture_ttl(namespace, params, producer, ttl=cache.DEFAULT_RESPONSE_TTL):
            nonlocal captured_ttl
            captured_ttl = ttl
            return await original_get_or_set(namespace, params, producer, ttl=ttl)

        class Client:
            async def get_total_count(self, path: str) -> int:
                nonlocal total_calls
                total_calls += 1
                return 10

        with patch("routers.translation.get_info_client", return_value=Client()), \
             patch("routers.translation.cache.get_or_set_response", capture_ttl):
            first = await all_stats()
            second = await all_stats()

        self.assertEqual(first, second)
        self.assertEqual(total_calls, 6)
        self.assertEqual(captured_ttl, 300)

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
        from services import cache
        from routers.translation import import_trans

        cache.set_response("categories", {}, [{"id": 7, "name_ja": "ドラマ"}], ttl=60)
        cache.set_response("translation_stats", {}, {"category": 0}, ttl=60)

        result = await import_trans(
            "category",
            await _upload_json({"7": {"name_ja": "ドラマ", "name_translated": "ドラマ"}}),
        )

        self.assertEqual(result["imported"], 1)
        self.assertEqual(get_translation("category:7")["category"]["ドラマ"], "ドラマ")
        self.assertIsNone(cache.get_response("categories", {}))
        self.assertIsNone(cache.get_response("translation_stats", {}))

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
            provider=None,
            mode="refresh_all",
        )

    async def test_start_job_accepts_single_provider(self):
        from routers.translation import start_translation_job

        with patch(
            "routers.translation.create_translation_job",
            AsyncMock(return_value={"id": 12, "status": "pending"}),
        ) as create_job:
            result = await start_translation_job({
                "job_type": "library_titles",
                "provider": "baidu",
                "mode": "remaining",
            })

        self.assertEqual(result["id"], 12)
        create_job.assert_awaited_once_with(
            "library_titles",
            provider_order=None,
            provider="baidu",
            mode="remaining",
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
            provider=None,
            mode="refresh_all",
        )

    async def test_workbench_manual_save_updates_mapping_and_history(self):
        from database import get_translation, upsert_translation_workbench_item
        from services import cache
        from routers.translation import get_translation_item_history, list_translation_items, update_translation_item

        cache.set_response("actresses", {"page": 1}, {"data": []}, ttl=60)
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
        self.assertIsNone(cache.get_response("actresses", {"page": 1}))

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

    async def test_workbench_default_list_uses_short_response_cache_with_bypass(self):
        from routers import translation

        with patch.object(translation, "_translation_items_payload", side_effect=[
            {"data": [{"item_id": "first"}], "total_count": 1, "page": 1, "page_size": 50, "total_pages": 1, "seeded": 0},
            {"data": [{"item_id": "fresh"}], "total_count": 1, "page": 1, "page_size": 50, "total_pages": 1, "seeded": 0},
        ]) as payload:
            first = await translation.list_translation_items(page=1, page_size=50)
            second = await translation.list_translation_items(page=1, page_size=50)
            bypassed = await translation.list_translation_items(page=1, page_size=50, cache_control="0")

        self.assertEqual(payload.call_count, 2)
        self.assertEqual(first["data"][0]["item_id"], "first")
        self.assertEqual(second["data"][0]["item_id"], "first")
        self.assertEqual(bypassed["data"][0]["item_id"], "fresh")

    async def test_workbench_cached_list_skips_authoritative_mapping_sync(self):
        from routers import translation

        with patch.object(translation, "sync_translation_workbench_from_mappings", return_value=4) as sync, \
             patch.object(
                 translation,
                 "_translation_items_payload",
                 return_value={
                     "data": [{"item_id": "cached"}],
                     "total_count": 1,
                     "page": 1,
                     "page_size": 50,
                     "total_pages": 1,
                     "seeded": 4,
                 },
             ) as payload:
            first = await translation.list_translation_items(item_type="category", page=1, page_size=50)
            second = await translation.list_translation_items(item_type="category", page=1, page_size=50)

        self.assertEqual(first, second)
        self.assertEqual(sync.call_count, 1)
        self.assertEqual(payload.call_count, 1)

    async def test_upsert_translation_invalidates_workbench_response_generation(self):
        from database import upsert_translation
        from services import cache

        before = cache.get_data_generation("translation_workbench")

        upsert_translation("category:7", {"category": {"ドラマ": "剧情"}})

        self.assertGreater(cache.get_data_generation("translation_workbench"), before)

    async def test_workbench_list_syncs_all_authoritative_mapping_rows_with_pagination(self):
        from database import upsert_translation
        from routers.translation import list_translation_items

        for index in range(0, 1005):
            upsert_translation(f"category:{index}", {"category": {f"原文{index:04d}": f"译文{index:04d}"}})

        listed = await list_translation_items(item_type="category", page=11, page_size=100)

        self.assertEqual(listed["total_count"], 1005)
        self.assertEqual(listed["total_pages"], 11)
        self.assertEqual(len(listed["data"]), 5)

    async def test_workbench_search_syncs_authoritative_mapping_rows_outside_first_page(self):
        from database import upsert_translation
        from routers.translation import list_translation_items

        for index in range(0, 1005):
            translated = "最后一个译文" if index == 1004 else f"译文{index:04d}"
            upsert_translation(f"category:{index}", {"category": {f"原文{index:04d}": translated}})

        listed = await list_translation_items(item_type="category", q="最后一个译文", page=1, page_size=20)

        self.assertEqual(listed["total_count"], 1)
        self.assertEqual(listed["data"][0]["item_id"], "1004")
        self.assertEqual(listed["data"][0]["translated_text"], "最后一个译文")

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

        reviewed = await update_translation_item("category", "7", {"action": "proofread"})
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
            provider=None,
        )

    async def test_retry_endpoint_accepts_single_provider(self):
        from routers.translation import retry_translation_items

        with patch(
            "routers.translation.create_translation_retry_job",
            AsyncMock(return_value={"id": 10, "status": "pending"}),
        ) as create_job:
            result = await retry_translation_items({"type": "title", "provider": "baidu"})

        self.assertEqual(result["id"], 10)
        create_job.assert_awaited_once_with(
            item_type="title",
            status=None,
            q=None,
            ids=None,
            provider_order=None,
            provider="baidu",
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
