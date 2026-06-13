"""Emby 兼容层契约测试（mock DB/info_client/resolver，无需 PostgreSQL）。"""
from __future__ import annotations

import asyncio
import hashlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

EMBY_CONFIG = {"emby_compat": {"enabled": True, "username": "javhub", "password": "secret"}}

RESOURCE_ROW = {
    "id": 7, "provider": "open115", "remote_file_id": "file-7",
    "parent_id": "folder-1", "pick_code": "pick-7",
    "name": "ABC-123.mp4", "extension": "mp4", "size": 1234,
    "duration": 7200, "movie_id": "ABC-123", "resource_type": "video",
    "status": "ready", "is_default": 1,
}

METADATA = {
    "content_id": "ABC-123",
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
        self.info_client = AsyncMock()
        self.info_client.list_catalog_videos.return_value = {
            "data": [METADATA],
            "total_count": 1,
            "page": 1,
            "page_size": 50,
        }
        self.info_client.get_catalog_video.return_value = METADATA
        self.patches = [
            patch("routers.emby_compat.config._config", EMBY_CONFIG),
            patch("routers.emby_compat.list_movie_resources", return_value=[RESOURCE_ROW]),
            patch("modules.info_client.get_info_client", return_value=self.info_client),
            patch("routers.emby_compat.get_progress", return_value=None),
            patch("routers.emby_compat.get_progress_map", return_value={}),
            patch("routers.emby_compat.movie_favorite_flags", return_value={}),
            patch("routers.emby_compat.is_movie_favorite", return_value=False),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_views_exposes_single_movie_library(self):
        from routers.emby_compat import user_views

        resp = asyncio.run(user_views("u", self.auth_req))
        self.assertEqual(resp["TotalRecordCount"], 1)
        self.assertEqual(resp["Items"][0]["CollectionType"], "movies")

    def test_items_browse_returns_catalog_movie_without_library_file(self):
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
        self.info_client.list_catalog_videos.assert_awaited_once_with(
            page=1,
            page_size=50,
            q=None,
            sort_by="release_date:desc",
            random_seed=None,
            include_total=True,
        )

    def test_items_browse_delegates_search_to_catalog(self):
        from routers.emby_compat import items_browse

        self.info_client.list_catalog_videos.return_value = {
            "data": [],
            "total_count": 0,
            "page": 1,
            "page_size": 50,
        }
        resp = asyncio.run(items_browse("u", self.auth_req, ParentId=None,
                                        StartIndex=0, Limit=50, SortBy="DateCreated",
                                        SortOrder="Descending", SearchTerm="zzz"))
        self.assertEqual(resp["TotalRecordCount"], 0)
        self.info_client.list_catalog_videos.assert_awaited_once_with(
            page=1,
            page_size=50,
            q="zzz",
            sort_by="release_date:desc",
            random_seed=None,
            include_total=True,
        )

    def test_items_browse_translates_emby_sort_fields_and_directions(self):
        from routers.emby_compat import items_browse

        cases = (
            ("ProductionYear", "Ascending", "release_date:asc"),
            ("SortName", "Descending", "title:desc"),
            ("CommunityRating", "Descending", "score:desc"),
            ("Runtime", "Ascending", "runtime_mins:asc"),
            (
                "SortName,ProductionYear",
                "Ascending,Descending",
                "title:asc,release_date:desc",
            ),
        )
        for sort_by, sort_order, expected in cases:
            with self.subTest(sort_by=sort_by, sort_order=sort_order):
                self.info_client.list_catalog_videos.reset_mock()
                asyncio.run(items_browse(
                    "u",
                    self.auth_req,
                    ParentId="library",
                    StartIndex=0,
                    Limit=50,
                    SortBy=sort_by,
                    SortOrder=sort_order,
                    SearchTerm=None,
                ))
                kwargs = self.info_client.list_catalog_videos.await_args.kwargs
                self.assertEqual(kwargs["sort_by"], expected)
                self.assertNotIn("sort_order", kwargs)

    def test_items_browse_uses_stable_session_seed_for_random_sort(self):
        from routers.emby_compat import items_browse

        asyncio.run(items_browse(
            "u",
            self.auth_req,
            ParentId="library",
            StartIndex=0,
            Limit=50,
            SortBy="Random",
            SortOrder="Ascending",
            SearchTerm=None,
        ))

        kwargs = self.info_client.list_catalog_videos.await_args.kwargs
        self.assertEqual(kwargs["sort_by"], "random:asc")
        self.assertEqual(
            kwargs["random_seed"],
            hashlib.sha256(self.token.encode("utf-8")).hexdigest()[:16],
        )

    def test_items_browse_rejects_unknown_emby_sort_field(self):
        from routers.emby_compat import items_browse

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(items_browse(
                "u",
                self.auth_req,
                ParentId="library",
                StartIndex=0,
                Limit=50,
                SortBy="UnsupportedField",
                SortOrder="Ascending",
                SearchTerm=None,
            ))

        self.assertEqual(ctx.exception.status_code, 400)

    def test_catalog_page_spans_api_pages_for_unaligned_start_index(self):
        from routers.emby_compat import _catalog_page

        self.info_client.list_catalog_videos.side_effect = [
            {
                "data": [{"content_id": f"item-{i}"} for i in range(50, 100)],
                "total_count": 200,
            },
            {
                "data": [{"content_id": f"item-{i}"} for i in range(100, 150)],
                "total_count": -1,
            },
        ]

        page = asyncio.run(_catalog_page(start_index=75, limit=50))

        self.assertEqual(
            [item["content_id"] for item in page["data"]],
            [f"item-{i}" for i in range(75, 125)],
        )
        self.assertEqual(page["total_count"], 200)
        calls = self.info_client.list_catalog_videos.await_args_list
        self.assertEqual(calls[0].kwargs["page"], 2)
        self.assertEqual(calls[0].kwargs["page_size"], 50)
        self.assertTrue(calls[0].kwargs["include_total"])
        self.assertEqual(calls[1].kwargs["page"], 3)
        self.assertFalse(calls[1].kwargs["include_total"])

    def test_item_detail_exists_without_library_file(self):
        from routers.emby_compat import item_detail

        with patch("routers.emby_compat.list_movie_resources", return_value=[]):
            item = asyncio.run(item_detail("u", "ABC-123", self.auth_req))

        self.assertEqual(item["Id"], "ABC-123")
        self.assertEqual(item["Type"], "Movie")
        self.assertEqual(item["SortName"], "テスト")
        self.assertEqual(item["DateCreated"], "2026-01-02T00:00:00.0000000Z")
        self.assertNotIn("MediaSources", item)

    def test_playback_info_marks_direct_play_without_transcoding(self):
        from routers.emby_compat import playback_info

        resp = asyncio.run(playback_info("ABC-123", self.auth_req))
        source = next(item for item in resp["MediaSources"] if item["Id"] == "open115:7")
        self.assertEqual(source["Id"], "open115:7")
        self.assertTrue(source["SupportsDirectPlay"])
        self.assertFalse(source["SupportsTranscoding"])
        self.assertIn("/Videos/ABC-123/stream.mp4", source["DirectStreamUrl"])

    def test_playback_info_offers_online_source_without_library_file(self):
        from routers.emby_compat import playback_info

        with patch("routers.emby_compat.list_movie_resources", return_value=[]):
            resp = asyncio.run(playback_info("ABC-123", self.auth_req))

        self.assertEqual(len(resp["MediaSources"]), 1)
        source = resp["MediaSources"][0]
        self.assertEqual(source["Id"], "online:auto")
        self.assertEqual(source["Container"], "m3u8")
        self.assertTrue(source["IsRemote"])
        self.assertIn("/Videos/ABC-123/stream.m3u8", source["DirectStreamUrl"])

    def test_stream_redirects_to_freshly_resolved_link(self):
        from routers.emby_compat import video_stream

        gateway = AsyncMock(return_value=type("R", (), {
            "status_code": 302,
            "headers": {"location": "https://cdn.example/v.mp4?sig=t"},
        })())
        with patch("routers.emby_compat.get_movie_resource", return_value=RESOURCE_ROW), \
             patch("routers.playback.stream_movie_resource", new=gateway):
            resp = asyncio.run(video_stream(
                "ABC-123", self.auth_req, ext="mp4", MediaSourceId="open115:7"
            ))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "https://cdn.example/v.mp4?sig=t")

    def test_online_stream_resolves_by_catalog_dvd_id_and_uses_safe_proxy(self):
        from routers.emby_compat import video_stream

        result = {"m3u8_url": "https://cdn.jable.tv/ABC-123/index.m3u8", "source": "jable"}
        with patch(
            "sources.m3u8_source.M3U8Source.search_m3u8",
            new=AsyncMock(return_value=(result, [])),
        ) as search_mock:
            resp = asyncio.run(
                video_stream("ABC-123", self.auth_req, ext="m3u8", MediaSourceId="online:auto")
            )

        search_mock.assert_awaited_once_with("ABC-123")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["location"].startswith("/api/v1/stream/proxy?url="))


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
