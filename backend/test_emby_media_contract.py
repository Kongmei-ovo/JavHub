from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient


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
    "jacket_full_url": "https://img.example/poster.jpg",
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
        from main import app

        cls.client = TestClient(app)

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

    def test_movie_person_backdrop_and_missing_images_never_404(self):
        info = AsyncMock()
        info.get_catalog_video.side_effect = [MOVIE, MOVIE, {}, {}]
        info.get_actress.return_value = {
            "id": 11,
            "name_kanji": "演员",
            "image_url": "https://img.example/person.jpg",
        }
        with patch("modules.info_client.get_info_client", return_value=info):
            primary = self.client.get(
                "/Items/stable:item-1/Images/Primary",
                follow_redirects=False,
            )
            backdrop = self.client.head(
                "/items/stable:item-1/images/backdrop/0",
                follow_redirects=False,
            )
            person = self.client.get(
                "/Items/person:11/Images/Primary",
                follow_redirects=False,
            )
            missing = self.client.get("/Items/missing/Images/Primary")
        self.assertEqual(primary.status_code, 302)
        self.assertEqual(backdrop.status_code, 302)
        self.assertEqual(person.headers["location"], "https://img.example/person.jpg")
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

    def test_original_and_hls_aliases_delegate_to_final_ua_gateway(self):
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
        self.assertEqual(hls.status_code, 302)
        self.assertEqual(gateway.await_args_list[0].kwargs["mode"], "original")
        self.assertEqual(gateway.await_args_list[1].kwargs["mode"], "hls")
        self.assertEqual(
            gateway.await_args_list[0].args[1].headers["user-agent"],
            "Infuse/8.1 AppleTV",
        )

    def test_cors_accepts_emby_headers_and_head(self):
        response = self.client.options(
            "/Items",
            headers={
                "Origin": "http://localhost:5174",
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
