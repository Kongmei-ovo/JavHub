from __future__ import annotations

import unittest

from fastapi import FastAPI

from test_support.client import ASGITestClient, create_test_client
from test_support.postgres import TempPostgresMixin


class LogsRouteTest(TempPostgresMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()

        from database import add_log

        add_log("INFO", "inventory collect started")
        add_log("WARNING", "inventory collect slow")
        add_log("ERROR", "downloader failed")

    def _client(self) -> ASGITestClient:
        from routers.logs import router

        app = FastAPI()
        app.include_router(router)
        return create_test_client(app)

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
