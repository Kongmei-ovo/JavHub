from __future__ import annotations

import unittest

from fastapi import FastAPI

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


if __name__ == "__main__":
    unittest.main()
