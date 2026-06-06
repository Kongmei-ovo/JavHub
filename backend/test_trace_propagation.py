from __future__ import annotations

import asyncio
import unittest

from fastapi import FastAPI

from test_support.client import create_router_test_client, create_test_client
from test_support.postgres import TempPostgresMixin


class TraceMiddlewareTest(unittest.TestCase):
    def test_concurrent_requests_get_isolated_trace_ids(self):
        from middlewares.trace import TraceIdMiddleware, get_trace_id

        app = FastAPI()
        app.add_middleware(TraceIdMiddleware)

        seen = asyncio.Queue()

        @app.get("/trace")
        async def trace():
            current = get_trace_id()
            await seen.put(current)
            await asyncio.sleep(0.01)
            return {"trace_id": get_trace_id()}

        async def request_pair():
            transport = __import__("httpx").ASGITransport(app=app)
            async with __import__("httpx").AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await asyncio.gather(client.get("/trace"), client.get("/trace"))

        first, second = asyncio.run(request_pair())

        first_header = first.headers.get("X-Trace-Id")
        second_header = second.headers.get("X-Trace-Id")
        self.assertRegex(first_header or "", r"^[0-9a-f]{8}$")
        self.assertRegex(second_header or "", r"^[0-9a-f]{8}$")
        self.assertNotEqual(first_header, second_header)
        self.assertEqual(first.json()["trace_id"], first_header)
        self.assertEqual(second.json()["trace_id"], second_header)

    def test_worker_submit_inherits_current_trace_id(self):
        from middlewares.trace import get_trace_id, set_trace_id
        from scheduler.worker_loop import submit

        async def read_trace_id():
            return get_trace_id()

        token = set_trace_id("cafebabe")
        try:
            future = submit(read_trace_id())
        finally:
            token.var.reset(token)

        self.assertEqual(future.result(timeout=2), "cafebabe")


class TraceLogsRouteTest(TempPostgresMixin, unittest.TestCase):
    def test_logs_filter_by_trace_id_and_return_trace_id_shape(self):
        from database import log as log_database
        from middlewares.trace import set_trace_id
        from routers.logs import router

        first_token = set_trace_id("deadbeef")
        try:
            log_database.add_log("INFO", "matching trace")
        finally:
            first_token.var.reset(first_token)

        second_token = set_trace_id("feedface")
        try:
            log_database.add_log("INFO", "other trace")
        finally:
            second_token.var.reset(second_token)

        response = create_router_test_client(router).get(
            "/api/v1/logs",
            params={"trace_id": "deadbeef", "cache": "0"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["trace_id"], "deadbeef")
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["message"], "matching trace")
        self.assertEqual(body["data"][0]["trace_id"], "deadbeef")


class AppTraceMiddlewareTest(unittest.TestCase):
    def test_main_app_registers_trace_middleware(self):
        import importlib
        import sys
        from unittest.mock import patch

        from middlewares.trace import TraceIdMiddleware

        sys.modules.pop("main", None)
        with patch("database.init_db"):
            main = importlib.import_module("main")

        trace_middleware = [
            middleware
            for middleware in main.app.user_middleware
            if middleware.cls is TraceIdMiddleware
        ]

        self.assertEqual(len(trace_middleware), 1)


if __name__ == "__main__":
    unittest.main()
