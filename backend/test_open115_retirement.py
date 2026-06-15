from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch


class Open115RuntimeRetirementTests(unittest.TestCase):
    def test_playback_router_has_no_scanned_library_or_openlist_resolver(self):
        from routers import playback

        source = inspect.getsource(playback)
        self.assertNotIn("get_library_files_by_content_id", source)
        self.assertNotIn("get_resolver", source)
        self.assertNotIn('@router.get("/library/', source)

    def test_scheduler_has_no_library_scan_job(self):
        from scheduler import tasks

        source = inspect.getsource(tasks)
        self.assertNotIn("library_scan_job", source)
        self.assertNotIn("services.library_scanner", source)
        self.assertNotIn("id='library_scan'", source)

    def test_main_does_not_register_library_index_router(self):
        main_source = (inspect.getsourcefile(self.__class__) and
                       open(inspect.getsourcefile(self.__class__).replace(
                           "test_open115_retirement.py", "main.py"
                       ), encoding="utf-8").read())
        self.assertNotIn("library_index_router", main_source)

    def test_database_no_longer_initializes_scanned_library_tables(self):
        from database import base

        source = inspect.getsource(base)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS library_files", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS library_scan_runs", source)
        self.assertNotIn("idx_library_files_", source)

    def test_config_updates_cannot_modify_legacy_openlist_section(self):
        from routers.config import update_config

        with patch("routers.config.config.update") as update:
            import asyncio

            asyncio.run(update_config({"openlist": {"token": "new"}, "open115": {"root_path": "/JavHub"}}))

        update.assert_called_once_with({"open115": {"root_path": "/JavHub"}})


if __name__ == "__main__":
    unittest.main()
