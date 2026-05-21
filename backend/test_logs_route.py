from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class LogsRouteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.db_patch = patch("database.base.DB_PATH", self.db_path)
        self.db_patch.start()

        from database import add_log, init_db

        init_db()
        add_log("INFO", "inventory collect started")
        add_log("WARNING", "inventory collect slow")
        add_log("ERROR", "downloader failed")

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def _client(self) -> TestClient:
        from routers.logs import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_logs_support_search_pagination_and_total(self):
        response = self._client().get(
            "/api/v1/logs",
            params={"q": "inventory", "limit": 1, "offset": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["offset"], 1)
        self.assertEqual(len(body["data"]), 1)
        self.assertIn("inventory", body["data"][0]["message"])

    def test_logs_filter_level_with_search(self):
        response = self._client().get(
            "/api/v1/logs",
            params={"level": "ERROR", "q": "downloader"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["data"][0]["level"], "ERROR")
        self.assertEqual(body["data"][0]["message"], "downloader failed")


if __name__ == "__main__":
    unittest.main()
