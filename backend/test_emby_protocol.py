from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


EMBY_CONFIG = {
    "server": {"port": 18090},
    "emby_compat": {
        "enabled": True,
        "username": "javhub",
        "password": "secret",
    },
}


class EmbyProtocolTests(unittest.TestCase):
    def setUp(self):
        from main import app
        from services.emby_auth import clear_compat_sessions

        clear_compat_sessions()
        self.config_patch = patch("config.config._config", EMBY_CONFIG)
        self.router_config_patch = patch("routers.emby_compat.config._config", EMBY_CONFIG)
        self.config_patch.start()
        self.router_config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.addCleanup(self.router_config_patch.stop)
        self.client = TestClient(app)

    def login(self) -> str:
        response = self.client.post(
            "/Users/AuthenticateByName",
            json={"Username": "javhub", "Pw": "secret"},
            headers={
                "X-Emby-Client": "Emby for iOS",
                "X-Emby-Device-Id": "device-1",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["AccessToken"]

    def test_emby_root_and_public_info_look_like_modern_emby(self):
        for path in ("/emby", "/emby/", "/System/Info/Public", "/emby/System/Info/Public"):
            response = self.client.get(path, headers={"host": "media.example:18090"})
            self.assertEqual(response.status_code, 200, (path, response.text))
            payload = response.json()
            self.assertEqual(payload["ProductName"], "Emby Server")
            self.assertTrue(payload["Version"].startswith("4."))
            self.assertEqual(payload["LocalAddress"], "http://media.example:18090")
            self.assertTrue(payload["StartupWizardCompleted"])

    def test_login_accepts_form_and_case_variants(self):
        response = self.client.post(
            "/emby/users/authenticatebyname",
            content="username=JAVHUB&password=secret",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["User"]["Name"], "javhub")

    def test_signed_token_survives_in_memory_session_reset(self):
        from services.emby_auth import clear_compat_sessions

        token = self.login()
        clear_compat_sessions()
        response = self.client.get(
            "/Users/Me",
            headers={"X-MediaBrowser-Token": token},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_password_change_invalidates_old_token(self):
        token = self.login()
        changed = {
            "server": {"port": 18090},
            "emby_compat": {
                "enabled": True,
                "username": "javhub",
                "password": "changed",
            },
        }
        with patch("config.config._config", changed), patch(
            "routers.emby_compat.config._config",
            changed,
        ):
            response = self.client.get("/Users/Me", headers={"X-Emby-Token": token})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["Code"], 40101)

    def test_official_client_probe_routes_never_404(self):
        token = self.login()
        auth = {"X-Emby-Token": token}
        info_client = AsyncMock()
        info_client.list_catalog_videos.return_value = {"data": [], "total_count": 0}
        probes = (
            ("GET", "/Startup/Configuration", None),
            ("GET", "/System/Configuration/Public", None),
            ("GET", "/QuickConnect/Enabled", None),
            ("GET", "/Users/Public", None),
            ("GET", "/Branding/Css", None),
            ("GET", "/Localization/Cultures", None),
            ("GET", "/CustomCssJS/Scripts", None),
            ("GET", "/embywebsocket", None),
            ("HEAD", "/embywebsocket", None),
            ("POST", "/Sessions/Capabilities/Full", None),
            ("GET", "/System/WakeOnLanInfo", auth),
            ("GET", "/ScheduledTasks", auth),
            ("GET", "/LiveTv/Recordings", auth),
            ("GET", "/System/ActivityLog/Entries", auth),
            ("GET", "/Web/ConfigurationPages", auth),
            ("GET", "/Items/Latest?UserId=javhub-emby-user", auth),
            ("GET", "/Items/Resume?UserId=javhub-emby-user", auth),
            ("GET", "/Genres", auth),
            ("GET", "/Shows/Upcoming", auth),
            ("GET", "/Items/demo/ThemeMedia", auth),
            ("GET", "/System/Ext/ServerDomains", auth),
            ("GET", "/Items/demo/Similar", auth),
            ("GET", "/Items/demo/ThumbnailSet", auth),
            ("GET", "/Items/demo/SpecialFeatures", auth),
            ("GET", "/Items/demo/Intros", auth),
            ("GET", "/Users/javhub-emby-user/Items/demo/SpecialFeatures", auth),
            ("GET", "/Users/javhub-emby-user/Items/demo/Intros", auth),
            ("GET", "/MediaSegments/demo", auth),
            ("GET", "/Shows/demo/Seasons", auth),
            ("GET", "/Shows/demo/Episodes", auth),
            ("GET", "/Users/javhub-emby-user/Shows/NextUp", auth),
            ("GET", "/Users/javhub-emby-user/Shows/Upcoming", auth),
            ("POST", "/Users/javhub-emby-user/Configuration", auth),
        )
        with patch("modules.info_client.get_info_client", return_value=info_client):
            for method, path, headers in probes:
                response = self.client.request(method, path, headers=headers)
                self.assertNotEqual(response.status_code, 404, (method, path, response.text))
                self.assertLess(response.status_code, 500, (method, path, response.text))

    def test_lowercase_public_and_head_routes_exist(self):
        for method, path in (
            ("GET", "/system/info/public"),
            ("HEAD", "/System/Info/Public"),
            ("GET", "/emby/quickconnect/enabled"),
            ("HEAD", "/emby/Branding/Css"),
            ("GET", "/emby/embywebsocket"),
            ("HEAD", "/emby/embywebsocket"),
        ):
            response = self.client.request(method, path)
            expected = 204 if path.endswith("embywebsocket") else 200
            self.assertEqual(response.status_code, expected, (method, path, response.text))


if __name__ == "__main__":
    unittest.main()
