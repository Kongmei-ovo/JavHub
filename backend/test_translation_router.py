from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
    async def test_stats_coverage_uses_javinfo_totals_and_dedupes_cache(self):
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
            "translated": 2,
            "untranslated": 1,
            "mapped": 1,
            "cached": 2,
        })
        self.assertEqual(stats["coverage"]["category"], {
            "total": 3,
            "translated": 2,
            "untranslated": 1,
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


if __name__ == "__main__":
    unittest.main()
