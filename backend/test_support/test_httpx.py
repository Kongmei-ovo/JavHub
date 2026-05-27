from __future__ import annotations

import unittest

import pytest

from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient


class RecordingAsyncClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_records_context_and_queued_responses(self):
        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("get", FakeHTTPResponse({"page": 1}))
        RecordingAsyncClient.add_response("get", FakeHTTPResponse({"page": 2}))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"created": True}, text="ok"))

        async with RecordingAsyncClient(timeout=3, trust_env=False) as client:
            first = await client.get("https://api.test/one", headers={"A": "1"})
            second = await client.get("https://api.test/two")
            created = await client.post("https://api.test/items", json={"name": "title"})

        self.assertEqual(first.json(), {"page": 1})
        self.assertEqual(second.json(), {"page": 2})
        self.assertEqual(created.text, "ok")
        self.assertEqual(created.json(), {"created": True})
        self.assertEqual(
            RecordingAsyncClient.calls,
            [
                {"method": "__init__", "args": (), "kwargs": {"timeout": 3, "trust_env": False}},
                {"method": "__aenter__", "args": (), "kwargs": {}},
                {"method": "get", "url": "https://api.test/one", "kwargs": {"headers": {"A": "1"}}},
                {"method": "get", "url": "https://api.test/two", "kwargs": {}},
                {"method": "post", "url": "https://api.test/items", "kwargs": {"json": {"name": "title"}}},
                {"method": "__aexit__", "args": (None, None, None), "kwargs": {}},
            ],
        )

    async def test_exposes_configured_cookies(self):
        cookies = {"session": "abc"}

        async with RecordingAsyncClient(cookies=cookies) as client:
            self.assertIs(client.cookies, cookies)


def test_fake_http_response_raises_for_error_status():
    response = FakeHTTPResponse({"error": "bad"}, status_code=500)

    with pytest.raises(RuntimeError, match="HTTP status 500"):
        response.raise_for_status()
