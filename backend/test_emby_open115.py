from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.responses import RedirectResponse

EMBY_CONFIG = {"emby_compat": {"enabled": True, "username": "javhub", "password": "secret"}}
RESOURCE = {
    "id": 9,
    "movie_id": "stable:item-1",
    "provider": "open115",
    "remote_file_id": "file-1",
    "pick_code": "pick-1",
    "name": "movie.mkv",
    "extension": "mkv",
    "size": 1234,
    "duration": 7200,
    "resource_type": "video",
    "status": "ready",
    "is_default": 1,
}


class FakeRequest:
    def __init__(self, headers=None, query=None, body=None):
        self.headers = headers or {}
        self.query_params = query or {}
        self._body = body or {}

    async def json(self):
        return self._body


def login():
    from routers import emby_compat

    with patch("routers.emby_compat.config._config", EMBY_CONFIG):
        return asyncio.run(emby_compat.authenticate_by_name(
            FakeRequest(body={"Username": "javhub", "Pw": "secret"})
        ))


class EmbyOpen115Tests(unittest.TestCase):
    def setUp(self):
        self.token = login()["AccessToken"]
        self.request = FakeRequest(
            headers={
                "X-Emby-Token": self.token,
                "User-Agent": "Infuse/8.1 AppleTV",
            }
        )

    def test_playback_info_uses_real_open115_files_as_media_sources(self):
        from routers.emby_compat import playback_info

        resources = [
            RESOURCE,
            {**RESOURCE, "id": 10, "remote_file_id": "file-2", "name": "bonus.mp4",
             "extension": "mp4", "size": 100, "is_default": 0},
            {**RESOURCE, "id": 11, "remote_file_id": "sub-1", "name": "movie.ass",
             "extension": "ass", "resource_type": "subtitle", "size": 1, "is_default": 0},
        ]
        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.list_movie_resources", return_value=resources):
            response = asyncio.run(playback_info("stable:item-1", self.request))

        sources = response["MediaSources"]
        self.assertEqual([source["Id"] for source in sources[:2]], ["open115:9", "open115:10"])
        self.assertEqual(sources[0]["Container"], "mkv")
        self.assertTrue(sources[0]["SupportsDirectPlay"])
        self.assertTrue(sources[0]["SupportsTranscoding"])
        self.assertIn("mode=hls", sources[0]["TranscodingUrl"])
        self.assertEqual(sources[-1]["Id"], "online:auto")
        self.assertNotIn("mono", repr(sources).lower())
        self.assertNotIn("digital", repr(sources).lower())
        self.assertNotIn("rental", repr(sources).lower())

    def test_movie_without_open115_resources_still_offers_online_source(self):
        from routers.emby_compat import playback_info

        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.list_movie_resources", return_value=[]):
            response = asyncio.run(playback_info("stable:item-1", self.request))

        self.assertEqual([source["Id"] for source in response["MediaSources"]], ["online:auto"])

    def test_playback_info_only_describes_sources_without_resolving_them(self):
        from routers.emby_compat import playback_info

        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.list_movie_resources", return_value=[RESOURCE]), \
             patch(
                 "services.open115.open115_client.downurl",
                 new=AsyncMock(side_effect=AssertionError("PlaybackInfo must not resolve 115")),
             ), \
             patch(
                 "sources.m3u8_source.M3U8Source.search_m3u8",
                 new=AsyncMock(side_effect=AssertionError("PlaybackInfo must not search online")),
             ):
            response = asyncio.run(playback_info("stable:item-1", self.request))

        self.assertEqual(
            [source["Id"] for source in response["MediaSources"]],
            ["open115:9", "online:auto"],
        )

    def test_stream_delegates_resource_to_ua_aware_gateway(self):
        from routers.emby_compat import video_stream

        gateway = AsyncMock(return_value=RedirectResponse("https://download.test/file", status_code=302))
        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.get_movie_resource", return_value=RESOURCE), \
             patch("routers.playback.stream_movie_resource", new=gateway):
            response = asyncio.run(video_stream(
                "stable:item-1",
                self.request,
                ext="mkv",
                MediaSourceId="open115:9",
                mode="original",
            ))

        self.assertEqual(response.status_code, 302)
        gateway.assert_awaited_once_with(
            9,
            self.request,
            mode="original",
            caller="emby",
        )

    def test_stream_rejects_resource_bound_to_another_movie(self):
        from fastapi import HTTPException
        from routers.emby_compat import video_stream

        with patch("routers.emby_compat.config._config", EMBY_CONFIG), \
             patch("routers.emby_compat.get_movie_resource", return_value={**RESOURCE, "movie_id": "other"}):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(video_stream(
                    "stable:item-1",
                    self.request,
                    ext="mkv",
                    MediaSourceId="open115:9",
                    mode="original",
                ))

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
