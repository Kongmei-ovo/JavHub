"""播放路由逻辑测试（mock DB 与 resolver，无需 PostgreSQL）。"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from services.openlist import ResolvedLink

FILE_ROW = {
    "id": 1, "backend": "openlist", "path": "/115/AV/ABC-123.mp4",
    "name": "ABC-123.mp4", "size": 100, "modified_at": "2026-01-01",
    "content_id": "ABC-123", "match_status": "matched",
}
SMALL_ROW = {**FILE_ROW, "id": 2, "name": "ABC-123-small.mp4", "path": "/115/AV/small.mp4", "size": 10}


class LibraryPlayTests(unittest.TestCase):
    def _call(self, content_id="ABC-123", file_id=None, files=None, resolver=None):
        from routers.playback import library_play

        resolver = resolver or AsyncMock(resolve_play_url=AsyncMock(
            return_value=ResolvedLink(url="https://cdn/x.mp4?sig=1")
        ))
        with patch("routers.playback.get_library_files_by_content_id", return_value=files if files is not None else [FILE_ROW, SMALL_ROW]), \
             patch("routers.playback.get_resolver", return_value=resolver), \
             patch("routers.playback.get_progress", return_value=None):
            return asyncio.run(library_play(content_id, file_id=file_id))

    def test_returns_resolved_link_and_largest_file_first(self):
        result = self._call()
        self.assertEqual(result["play"]["url"], "https://cdn/x.mp4?sig=1")
        self.assertEqual(result["file"]["id"], 1)  # size 最大者
        self.assertEqual(len(result["files"]), 2)

    def test_response_never_contains_resolver_internals(self):
        result = self._call()
        for f in [result["file"], *result["files"]]:
            self.assertNotIn("ref_payload", f)

    def test_404_when_not_in_library(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            self._call(files=[])
        self.assertEqual(ctx.exception.status_code, 404)

    def test_selects_explicit_file_id(self):
        result = self._call(file_id=2)
        self.assertEqual(result["file"]["id"], 2)

    def test_502_when_resolver_fails(self):
        from fastapi import HTTPException

        resolver = AsyncMock(resolve_play_url=AsyncMock(side_effect=RuntimeError("boom")))
        with self.assertRaises(HTTPException) as ctx:
            self._call(resolver=resolver)
        self.assertEqual(ctx.exception.status_code, 502)


class ProgressEndpointTests(unittest.TestCase):
    def test_put_progress_validates_source(self):
        from fastapi import HTTPException

        from routers.playback import ProgressRequest, put_progress

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(put_progress("ABC-123", ProgressRequest(source="emby", position_seconds=1)))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_put_progress_saves(self):
        from routers.playback import ProgressRequest, put_progress

        with patch("routers.playback.save_progress", return_value={"content_id": "ABC-123"}) as mock_save:
            asyncio.run(put_progress("ABC-123", ProgressRequest(
                source="library", position_seconds=120, duration_seconds=7200,
            )))
        mock_save.assert_called_once_with("ABC-123", "library", 120, 7200)


if __name__ == "__main__":
    unittest.main()
