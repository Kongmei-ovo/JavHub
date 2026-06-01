from __future__ import annotations

import importlib
import sys
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from middlewares.performance import RequestTimingMiddleware
from test_support.client import create_test_client


class RequestTimingMiddlewareTest(unittest.TestCase):
    def test_response_includes_process_time_header(self):
        app = FastAPI()
        app.add_middleware(RequestTimingMiddleware, slow_request_ms=1000)

        @app.get("/ok")
        async def ok():
            return {"ok": True}

        response = create_test_client(app).get("/ok")

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.headers.get("X-Process-Time-Ms", ""), r"^\d+\.\d{2}$")


class AppCompressionMiddlewareTest(unittest.TestCase):
    def test_main_app_enables_gzip_for_large_json_responses(self):
        sys.modules.pop("main", None)
        with patch("database.init_db"):
            main = importlib.import_module("main")

        gzip_middleware = [
            middleware
            for middleware in main.app.user_middleware
            if middleware.cls is GZipMiddleware
        ]

        self.assertEqual(len(gzip_middleware), 1)
        self.assertEqual(gzip_middleware[0].kwargs, {"minimum_size": 1024})


if __name__ == "__main__":
    unittest.main()
