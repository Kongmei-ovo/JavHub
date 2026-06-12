"""Emby 兼容层契约测试（mock DB/info_client/resolver，无需 PostgreSQL）。"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from services.openlist import ResolvedLink

EMBY_CONFIG = {"emby_compat": {"enabled": True, "username": "javhub", "password": "secret"}}

FILE_ROW = {
    "id": 7, "backend": "openlist", "path": "/115/AV/ABC-123.mp4",
    "name": "ABC-123.mp4", "size": 1234, "content_id": "ABC-123",
    "match_status": "matched", "first_seen_at": "2026-06-01",
}

METADATA = {
    "title_ja": "テスト", "dvd_id": "ABC-123", "release_date": "2026-01-02",
    "runtime_mins": 120, "score": 4.5, "summary": "概要",
    "actresses": [{"id": 11, "name_kanji": "演员A"}],
    "categories": [{"name_ja": "题材X"}],
    "jacket_full_url": "https://img.example/jacket.jpg",
}


class FakeRequest:
    def __init__(self, headers=None, query=None, body=None):
        self.headers = headers or {}
        self.query_params = query or {}
        self._body = body or {}

    async def json(self):
        return self._body


def _login():
    from routers import emby_compat

    req = FakeRequest(body={"Username": "javhub", "Pw": "secret"})
    with patch("routers.emby_compat.config._config", EMBY_CONFIG):
        return asyncio.run(emby_compat.authenticate_by_name(req))


class AuthTests(unittest.TestCase):
    def test_authenticate_returns_token_and_user(self):
        resp = _login()
        self.assertTrue(resp["AccessToken"])
        self.assertEqual(resp["User"]["Name"], "javhub")
        self.assertTrue(resp["ServerId"])

    def test_authenticate_rejects_wrong_password(self):
        from routers import emby_compat

        req = FakeRequest(body={"Username": "javhub", "Pw": "wrong"})
        with patch("routers.emby_compat.config._config", EMBY_CONFIG):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(emby_compat.authenticate_by_name(req))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_rejects_when_disabled(self):
        from routers import emby_compat

        req = FakeRequest(body={"Username": "javhub", "Pw": "secret"})
        with patch("routers.emby_compat.config._config", {"emby_compat": {"enabled": False}}):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(emby_compat.authenticate_by_name(req))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_token_accepted_via_three_channels(self):
        from routers import emby_compat

        token = _login()["AccessToken"]
        with patch("routers.emby_compat.config._config", EMBY_CONFIG):
            for req in (
                FakeRequest(headers={"X-Emby-Token": token}),
                FakeRequest(headers={"X-MediaBrowser-Token": token}),
                FakeRequest(query={"api_key": token}),
            ):
                self.assertEqual(emby_compat._require_auth(req), token)
            with self.assertRaises(HTTPException):
                emby_compat._require_auth(FakeRequest())


class BrowseTests(unittest.TestCase):
    def setUp(self):
        from routers import emby_compat

        self.token = _login()["AccessToken"]
        self.auth_req = FakeRequest(headers={"X-Emby-Token": self.token})
        self.patches = [
            patch("routers.emby_compat.config._config", EMBY_CONFIG),
            patch("routers.emby_compat.list_matched_library_files", return_value=[FILE_ROW]),
            patch("routers.emby_compat.get_library_files_by_content_id", return_value=[FILE_ROW]),
            patch("routers.emby_compat._metadata_for", new=AsyncMock(return_value={"ABC-123": METADATA})),
            patch("routers.emby_compat.get_progress", return_value=None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_views_exposes_single_movie_library(self):
        from routers.emby_compat import user_views

        resp = asyncio.run(user_views("u", self.auth_req))
        self.assertEqual(resp["TotalRecordCount"], 1)
        self.assertEqual(resp["Items"][0]["CollectionType"], "movies")

    def test_items_browse_returns_base_item_dto(self):
        from routers.emby_compat import items_browse

        resp = asyncio.run(items_browse("u", self.auth_req, ParentId="library",
                                        StartIndex=0, Limit=50, SortBy="DateCreated",
                                        SortOrder="Descending", SearchTerm=None))
        self.assertEqual(resp["TotalRecordCount"], 1)
        item = resp["Items"][0]
        self.assertEqual(item["Id"], "ABC-123")
        self.assertEqual(item["Type"], "Movie")
        self.assertEqual(item["ProductionYear"], 2026)
        self.assertEqual(item["RunTimeTicks"], 120 * 60 * 10_000_000)
        self.assertEqual(item["People"][0]["Name"], "演员A")

    def test_items_browse_search_filters(self):
        from routers.emby_compat import items_browse

        resp = asyncio.run(items_browse("u", self.auth_req, ParentId=None,
                                        StartIndex=0, Limit=50, SortBy="DateCreated",
                                        SortOrder="Descending", SearchTerm="zzz"))
        self.assertEqual(resp["TotalRecordCount"], 0)

    def test_playback_info_marks_direct_play_without_transcoding(self):
        from routers.emby_compat import playback_info

        resp = asyncio.run(playback_info("ABC-123", self.auth_req))
        source = resp["MediaSources"][0]
        self.assertEqual(source["Id"], "lib:7")
        self.assertTrue(source["SupportsDirectPlay"])
        self.assertFalse(source["SupportsTranscoding"])
        self.assertIn("/Videos/ABC-123/stream.mp4", source["DirectStreamUrl"])

    def test_stream_redirects_to_freshly_resolved_link(self):
        from routers.emby_compat import video_stream

        resolver = AsyncMock(resolve_play_url=AsyncMock(
            return_value=ResolvedLink(url="https://cdn.example/v.mp4?sig=t")
        ))
        with patch("routers.emby_compat.get_resolver", return_value=resolver):
            resp = asyncio.run(video_stream("ABC-123", self.auth_req, ext="mp4", MediaSourceId="lib:7"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "https://cdn.example/v.mp4?sig=t")


class SessionProgressTests(unittest.TestCase):
    def test_progress_ticks_converted_and_saved(self):
        from routers import emby_compat

        token = _login()["AccessToken"]
        req = FakeRequest(
            headers={"X-Emby-Token": token},
            body={"ItemId": "ABC-123", "PositionTicks": 1230 * 10_000_000, "RunTimeTicks": 7200 * 10_000_000},
        )
        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.save_progress") as mock_save:
            resp = asyncio.run(emby_compat.session_progress(req))
        self.assertEqual(resp.status_code, 204)
        mock_save.assert_called_once_with("ABC-123", "library", 1230.0, 7200.0)


class EmptyFallbackTests(unittest.TestCase):
    def test_unimplemented_collection_endpoints_return_200_empty(self):
        from routers.emby_compat import router

        registered = {route.path for route in router.routes}
        for path in ("/Shows/NextUp", "/Persons", "/Items/Filters", "/Movies/Recommendations"):
            self.assertIn(path, registered, f"{path} should be registered as empty-set endpoint")


if __name__ == "__main__":
    unittest.main()
