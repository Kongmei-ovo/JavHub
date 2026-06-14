from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from test_support.client import load_main_app_without_db


EMBY_CONFIG = {
    "server": {"frontend_origin": "http://localhost:5174"},
    "emby_compat": {
        "enabled": True,
        "username": "javhub",
        "password": "secret",
    },
}

MOVIE = {
    "content_id": "stable:item-1",
    "dvd_id": "ABC-123",
    "title_ja": "作品",
    "jacket_thumb_url": "https://img.example/card.jpg",
    "jacket_full_url": "https://img.example/detail.jpg",
    "sample_image_urls": [
        "https://img.example/backdrop-1.jpg",
        "https://img.example/backdrop-2.jpg",
    ],
}

RESOURCE = {
    "id": 9,
    "movie_id": "stable:item-1",
    "provider": "open115",
    "remote_file_id": "file-1",
    "pick_code": "pick-1",
    "name": "movie.mkv",
    "extension": "mkv",
    "size": 4096,
    "duration": 7200,
    "resource_type": "video",
    "status": "ready",
    "is_default": 1,
}


class EmbyMediaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from config import config

        cls.frontend_origin = config.frontend_origin
        cls.client = TestClient(load_main_app_without_db())

    def setUp(self):
        self.config_patch = patch("config.config._config", EMBY_CONFIG)
        self.router_config_patch = patch("routers.emby_compat.config._config", EMBY_CONFIG)
        self.config_patch.start()
        self.router_config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.addCleanup(self.router_config_patch.stop)
        login = self.client.post(
            "/Users/AuthenticateByName",
            json={"Username": "javhub", "Pw": "secret"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.token = login.json()["AccessToken"]
        self.auth = {
            "X-Emby-Token": self.token,
            "User-Agent": "Infuse/8.1 AppleTV",
        }

    def test_movie_images_use_card_cover_and_real_indexed_backdrops(self):
        info = AsyncMock()
        info.get_catalog_video.return_value = MOVIE
        with patch("modules.info_client.get_info_client", return_value=info):
            primary = self.client.get(
                "/Items/stable:item-1/Images/Primary",
                follow_redirects=False,
            )
            first_backdrop = self.client.head(
                "/items/stable:item-1/images/backdrop/0",
                follow_redirects=False,
            )
            second_backdrop = self.client.head(
                "/Items/stable:item-1/Images/Backdrop/1",
                follow_redirects=False,
            )
            missing_backdrop = self.client.get(
                "/Items/stable:item-1/Images/Backdrop/9",
                follow_redirects=False,
            )
            unsupported_logo = self.client.get(
                "/Items/stable:item-1/Images/Logo",
                follow_redirects=False,
            )
        self.assertEqual(primary.headers["location"], "https://img.example/card.jpg")
        self.assertEqual(
            first_backdrop.headers["location"],
            "https://img.example/backdrop-1.jpg",
        )
        self.assertEqual(
            second_backdrop.headers["location"],
            "https://img.example/backdrop-2.jpg",
        )
        self.assertEqual(missing_backdrop.status_code, 200)
        self.assertEqual(missing_backdrop.headers["content-type"], "image/png")
        self.assertEqual(unsupported_logo.status_code, 200)
        self.assertEqual(unsupported_logo.headers["content-type"], "image/png")

    def test_missing_backdrop_does_not_reuse_primary_cover(self):
        info = AsyncMock()
        info.get_catalog_video.return_value = {
            **MOVIE,
            "sample_image_urls": [],
            "backdrop_url": "",
        }
        with patch("modules.info_client.get_info_client", return_value=info):
            backdrop = self.client.get(
                "/Items/stable:item-1/Images/Backdrop/0",
                follow_redirects=False,
            )
        self.assertEqual(backdrop.status_code, 200)
        self.assertEqual(backdrop.headers["content-type"], "image/png")

    def test_person_relative_avatar_and_missing_images_never_404(self):
        info = AsyncMock()
        info.get_catalog_video.return_value = {}
        info.get_actress.return_value = {
            "id": 11,
            "name_kanji": "演员",
            "image_url": "actress.jpg",
        }
        with patch("modules.info_client.get_info_client", return_value=info):
            person = self.client.get(
                "/Items/person:11/Images/Primary",
                follow_redirects=False,
            )
            missing = self.client.get("/Items/missing/Images/Primary")
        self.assertEqual(
            person.headers["location"],
            "https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/actress.jpg",
        )
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.headers["content-type"], "image/png")

    def test_playback_info_uses_stable_urls_and_default_resource_first(self):
        resources = [
            {**RESOURCE, "id": 10, "name": "bonus.mp4", "extension": "mp4", "is_default": 0},
            RESOURCE,
        ]
        with patch("routers.emby_compat.list_movie_resources", return_value=resources):
            response = self.client.post(
                "/Users/javhub-emby-user/Items/stable:item-1/PlaybackInfo",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        sources = response.json()["MediaSources"]
        self.assertEqual(sources[0]["Id"], "open115:9")
        self.assertEqual(sources[-1]["Id"], "online:auto")
        self.assertEqual(sources[0]["Path"], sources[0]["DirectStreamUrl"])
        self.assertIn("/Videos/stable:item-1/stream.mkv", sources[0]["Path"])

    def test_get_delegates_to_final_gateway_but_head_only_probes(self):
        gateway = AsyncMock(
            return_value=RedirectResponse("https://download.example/file", status_code=302)
        )
        with patch("routers.emby_compat.get_movie_resource", return_value=RESOURCE), patch(
            "routers.playback.stream_movie_resource",
            new=gateway,
        ):
            original = self.client.get(
                "/videos/stable:item-1/original.mkv?MediaSourceId=open115:9",
                headers=self.auth,
                follow_redirects=False,
            )
            hls = self.client.head(
                "/Videos/stable:item-1/main.m3u8?MediaSourceId=open115:9",
                headers=self.auth,
                follow_redirects=False,
            )
        self.assertEqual(original.status_code, 302)
        self.assertEqual(hls.status_code, 200)
        self.assertEqual(gateway.await_args_list[0].kwargs["mode"], "original")
        self.assertEqual(gateway.await_count, 1)
        self.assertEqual(
            gateway.await_args_list[0].args[1].headers["user-agent"],
            "Infuse/8.1 AppleTV",
        )

    def test_online_head_probe_never_searches_for_a_source(self):
        search = AsyncMock(
            side_effect=AssertionError("HEAD probe must not search online sources")
        )
        with patch(
            "sources.m3u8_source.M3U8Source.search_m3u8",
            new=search,
        ):
            response = self.client.head(
                "/Videos/stable:item-1/stream.m3u8?MediaSourceId=online:auto",
                headers=self.auth,
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 200)
        search.assert_not_awaited()

    def test_cors_accepts_emby_headers_and_head(self):
        response = self.client.options(
            "/Items",
            headers={
                "Origin": self.frontend_origin,
                "Access-Control-Request-Method": "HEAD",
                "Access-Control-Request-Headers": "X-Emby-Token,X-MediaBrowser-Token",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("HEAD", response.headers["access-control-allow-methods"])
        allowed = response.headers["access-control-allow-headers"].lower()
        self.assertIn("x-emby-token", allowed)
        self.assertIn("x-mediabrowser-token", allowed)


if __name__ == "__main__":
    unittest.main()
