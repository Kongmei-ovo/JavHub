from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.client import create_router_test_client


class Open115RoutesTests(unittest.TestCase):
    def _client(self):
        from routers.open115 import router

        return create_router_test_client(router)

    def test_status_never_returns_tokens(self):
        client = AsyncMock()
        client.status = Mock()
        client.status.return_value = {
            "configured": True,
            "bound": True,
            "access_token_configured": True,
            "refresh_token_configured": True,
        }

        with patch("routers.open115.open115_client", client):
            response = self._client().get("/api/v1/open115/status")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["bound"])
        self.assertNotIn("access_token", body)
        self.assertNotIn("refresh_token", body)

    def test_auth_start_returns_browser_safe_qr_metadata(self):
        client = AsyncMock()
        client.qrcode_image_url = Mock()
        client.start_device_auth.return_value = {"uid": "uid-1", "qrcode": "qr-content"}
        client.qrcode_image_url.return_value = "https://qrcode.test/image?uid=uid-1"

        with patch("routers.open115.open115_client", client):
            response = self._client().post("/api/v1/open115/auth/start")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "uid": "uid-1",
            "qrcode": "qr-content",
            "qrcode_image_url": "https://qrcode.test/image?uid=uid-1",
        })

    def test_import_only_returns_binding_result(self):
        client = AsyncMock()
        client.import_refresh_token.return_value = {"bound": True}

        with patch("routers.open115.open115_client", client):
            response = self._client().post(
                "/api/v1/open115/auth/import",
                json={"refresh_token": "secret-refresh"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"bound": True})
        client.import_refresh_token.assert_awaited_once_with("secret-refresh")

    def test_test_connection_maps_protocol_failure_to_502(self):
        from services.open115 import Open115Error

        client = AsyncMock()
        client.test_connection.side_effect = Open115Error(401, "unauthorized")

        with patch("routers.open115.open115_client", client):
            response = self._client().post("/api/v1/open115/test")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret", response.text)

    def test_unbind_clears_client_state(self):
        client = AsyncMock()
        client.unbind = Mock(return_value=None)

        with patch("routers.open115.open115_client", client):
            response = self._client().post("/api/v1/open115/unbind")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"bound": False})
        client.unbind.assert_called_once_with()

    def test_unbind_reports_environment_managed_binding(self):
        from services.open115 import Open115Error

        client = AsyncMock()
        client.unbind = Mock(side_effect=Open115Error(None, "授权由环境变量管理"))

        with patch("routers.open115.open115_client", client):
            response = self._client().post("/api/v1/open115/unbind")

        self.assertEqual(response.status_code, 409)
        self.assertIn("环境变量", response.json()["detail"])

    def test_status_exposes_verification_without_exposing_tokens(self):
        client = AsyncMock()
        client.status = Mock(return_value={
            "configured": True,
            "bound": True,
            "verified": True,
            "refresh_token_configured": True,
        })

        with patch("routers.open115.open115_client", client):
            response = self._client().get("/api/v1/open115/status")

        self.assertTrue(response.json()["verified"])
        self.assertNotIn("refresh_token", response.json())


if __name__ == "__main__":
    unittest.main()
