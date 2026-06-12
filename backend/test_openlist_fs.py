from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient

OPENLIST_CONFIG = {"openlist": {"api_url": "http://openlist", "token": "tok", "default_path": "/115/AV"}}


def _client():
    from services.openlist import OpenListClient

    return OpenListClient()


class FsListTests(unittest.TestCase):
    def setUp(self):
        RecordingAsyncClient.reset()

    def test_fs_list_aggregates_pages(self):
        page1 = {
            "code": 200,
            "data": {
                "total": 3,
                "content": [
                    {"name": "ABC-123.mp4", "is_dir": False, "size": 100, "modified": "2026-01-01T00:00:00Z", "sign": "s1"},
                    {"name": "subdir", "is_dir": True, "size": 0, "modified": ""},
                ],
            },
        }
        page2 = {
            "code": 200,
            "data": {
                "total": 3,
                "content": [
                    {"name": "DEF-456.mkv", "is_dir": False, "size": 200, "modified": "2026-01-02T00:00:00Z"},
                ],
            },
        }
        RecordingAsyncClient.add_response("post", FakeHTTPResponse(page1))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse(page2))

        with patch("services.openlist.config._config", OPENLIST_CONFIG), \
             patch("services.openlist.httpx.AsyncClient", RecordingAsyncClient):
            entries = asyncio.run(_client().fs_list("/115/AV"))

        self.assertEqual([e.name for e in entries], ["ABC-123.mp4", "subdir", "DEF-456.mkv"])
        self.assertEqual(entries[0].path, "/115/AV/ABC-123.mp4")
        self.assertTrue(entries[1].is_dir)
        self.assertEqual(entries[2].size, 200)
        post_calls = [c for c in RecordingAsyncClient.calls if c["method"] == "post"]
        self.assertEqual(len(post_calls), 2)
        self.assertEqual(post_calls[1]["kwargs"]["json"]["page"], 2)

    def test_fs_list_retries_after_token_expired(self):
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"code": 401, "message": "expired"}))
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse({"code": 200, "data": {"total": 1, "content": [
                {"name": "ABC-123.mp4", "is_dir": False, "size": 1, "modified": ""},
            ]}}),
        )

        async def fake_refresh(self):
            self.token = "new-token"
            return True

        with patch("services.openlist.config._config", OPENLIST_CONFIG), \
             patch("services.openlist.httpx.AsyncClient", RecordingAsyncClient), \
             patch("services.openlist.OpenListClient._refresh_token", fake_refresh):
            entries = asyncio.run(_client().fs_list("/115/AV"))

        self.assertEqual(len(entries), 1)

    def test_fs_list_raises_on_error_code(self):
        from services.openlist import OpenListFsError

        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"code": 500, "message": "storage offline"}))

        with patch("services.openlist.config._config", OPENLIST_CONFIG), \
             patch("services.openlist.httpx.AsyncClient", RecordingAsyncClient):
            with self.assertRaises(OpenListFsError) as ctx:
                asyncio.run(_client().fs_list("/115/AV"))
        self.assertEqual(ctx.exception.path, "/115/AV")


class ResolveLinkTests(unittest.TestCase):
    def setUp(self):
        RecordingAsyncClient.reset()

    def test_resolve_link_prefers_raw_url(self):
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse({"code": 200, "data": {"raw_url": "https://cdn.example/file.mp4?t=1", "sign": "sig"}}),
        )
        with patch("services.openlist.config._config", OPENLIST_CONFIG), \
             patch("services.openlist.httpx.AsyncClient", RecordingAsyncClient):
            link = asyncio.run(_client().resolve_link("/115/AV/ABC-123.mp4"))
        self.assertEqual(link.url, "https://cdn.example/file.mp4?t=1")
        self.assertEqual(link.kind, "direct")

    def test_resolve_link_falls_back_to_d_route(self):
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse({"code": 200, "data": {"raw_url": "", "sign": "sig123"}}),
        )
        with patch("services.openlist.config._config", OPENLIST_CONFIG), \
             patch("services.openlist.httpx.AsyncClient", RecordingAsyncClient):
            link = asyncio.run(_client().resolve_link("/115/AV/ABC-123.mp4"))
        self.assertEqual(link.url, "http://openlist/d/115/AV/ABC-123.mp4?sign=sig123")


if __name__ == "__main__":
    unittest.main()
