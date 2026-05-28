from __future__ import annotations

import unittest
from unittest import mock

from test_support.client import ASGIClient, create_router_test_client
from test_support.postgres import TempPostgresMixin


class LogsRouteTest(TempPostgresMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()

        from database import add_log

        add_log("INFO", "inventory collect started")
        add_log("WARNING", "inventory collect slow")
        add_log("ERROR", "downloader failed")

    def _client(self) -> ASGIClient:
        from routers.logs import router

        return create_router_test_client(router)

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

    def test_logs_listing_is_loaded_from_database_layer(self):
        expected_rows = [
            {
                "id": 101,
                "level": "ERROR",
                "message": "inventory delegated",
                "created_at": "2026-05-28 00:00:00",
            }
        ]

        with (
            mock.patch("routers.logs.get_db_orig", create=True, side_effect=AssertionError("router touched db")),
            mock.patch("database.log.list_logs", create=True, return_value=(expected_rows, 7)) as list_logs,
        ):
            response = self._client().get(
                "/api/v1/logs",
                params={"level": "error", "q": "inventory", "limit": 1, "offset": 2},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"data": expected_rows, "total": 7, "limit": 1, "offset": 2},
        )
        list_logs.assert_called_once_with(limit=1, level="ERROR", q="inventory", offset=2)

    def test_clear_logs_is_loaded_from_database_layer(self):
        with (
            mock.patch("routers.logs.get_db_orig", create=True, side_effect=AssertionError("router touched db")),
            mock.patch("database.log.clear_logs", create=True) as clear_logs,
        ):
            response = self._client().delete("/api/v1/logs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        clear_logs.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
