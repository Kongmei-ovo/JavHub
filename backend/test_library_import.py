from __future__ import annotations

import unittest
from unittest.mock import patch

from test_support.postgres import TempPostgresMixin


def _file(file_id, name, *, is_dir=False, pick_code="pc", extension="", size=100):
    from services.open115 import Open115File

    return Open115File(
        file_id=file_id, parent_id="ROOT", name=name, pick_code=pick_code,
        is_dir=is_dir, size=size, duration=0, extension=extension,
    )


class LibraryImportTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_backfill_imports_v1_dirs_and_skips_manual(self):
        from database import code_has_ready_resource
        from services import library_import
        from services.open115_downloader import Open115DownloaderClient, encode_movie_directory

        dir_a = _file("DA", encode_movie_directory("ABC-123"), is_dir=True, pick_code="")
        dir_b = _file("DB", encode_movie_directory("DEF-456"), is_dir=True, pick_code="")
        manual = _file("DM", "手工目录", is_dir=True, pick_code="")
        tree = {
            "ROOT": [dir_a, dir_b, manual],
            "DA": [_file("v1", "ABC-123.mp4", extension="mp4"), _file("s1", "ABC-123.srt", extension="srt")],
            "DB": [_file("v2", "DEF-456.mp4", extension="mp4"), _file("s2", "DEF-456.srt", extension="srt")],
        }

        class FakeClient:
            root_path = "/JavHub"

            async def ensure_folder_path(self, path):
                return "ROOT"

            async def iter_files(self, folder_id):
                for item in tree.get(folder_id, []):
                    yield item

            async def walk_files(self, folder_id):
                for item in tree.get(folder_id, []):
                    yield item

        fake = FakeClient()
        downloader = Open115DownloaderClient(client=fake)
        result = await library_import.import_115_library(client=fake, downloader=downloader)

        self.assertEqual(result["imported_movies"], 2)
        self.assertEqual(result["imported_videos"], 2)
        self.assertEqual(result["imported_subtitles"], 2)
        self.assertEqual(result["skipped_dirs"], 1)  # the manual (undecodable) dir
        self.assertTrue(code_has_ready_resource("ABC-123"))
        self.assertTrue(code_has_ready_resource("DEF-456"))

    async def test_parity_lists_codes_only_in_emby(self):
        from database import upsert_movie_resource
        from modules.code_matcher import normalize_code
        from services import library_import

        upsert_movie_resource(movie_id="ABC-1", provider="open115", remote_file_id="v1",
                              name="ABC-1.mp4", status="ready", is_default=True)
        upsert_movie_resource(movie_id="DEF-2", provider="open115", remote_file_id="v2",
                              name="DEF-2.mp4", status="ready", is_default=True)

        emby = {normalize_code("ABC-1"), normalize_code("DEF-2"), normalize_code("GHI-3")}
        with patch("services.subscription._load_latest_existing_codes", return_value=emby):
            report = library_import.emby_resource_parity()

        self.assertEqual(report["only_in_emby"], [normalize_code("GHI-3")])  # the un-backfilled one
        self.assertEqual(report["only_in_resources"], [])
        self.assertFalse(report["ready_for_de_emby"])  # gate stays closed

    async def test_parity_clears_when_resources_cover_emby(self):
        from database import upsert_movie_resource
        from modules.code_matcher import normalize_code
        from services import library_import

        upsert_movie_resource(movie_id="ABC-1", provider="open115", remote_file_id="v1",
                              name="ABC-1.mp4", status="ready", is_default=True)

        emby = {normalize_code("ABC-1")}
        with patch("services.subscription._load_latest_existing_codes", return_value=emby):
            report = library_import.emby_resource_parity()

        self.assertEqual(report["only_in_emby"], [])
        self.assertTrue(report["ready_for_de_emby"])  # gate opens → P6 allowed
        self.assertEqual(report["parity_ratio"], 1.0)


class MigrationRouteTests(TempPostgresMixin, unittest.TestCase):
    def test_parity_endpoint_returns_report(self):
        from test_support.client import create_router_test_client
        from routers.migration import router

        with patch("services.subscription._load_latest_existing_codes", return_value=set()):
            resp = create_router_test_client(router).get("/api/v1/migration/parity")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("ready_for_de_emby", body)
        self.assertIn("only_in_emby", body)


if __name__ == "__main__":
    unittest.main()
