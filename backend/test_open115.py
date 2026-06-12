from __future__ import annotations

import asyncio
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx
import yaml


class SequenceHTTPClient:
    def __init__(self, responses: list[Any]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        response = self.responses.pop(0)
        if callable(response):
            response = response(method, url, kwargs)
        return response

    async def aclose(self) -> None:
        return None


def response(payload: dict, *, status_code: int = 200, url: str = "https://115.test/api") -> httpx.Response:
    return httpx.Response(
        status_code,
        request=httpx.Request("GET", url),
        json=payload,
    )


class Open115ClientTests(unittest.IsolatedAsyncioTestCase):
    def _config(self, root: Path, section: dict | None = None) -> SimpleNamespace:
        config_path = root / "config.yaml"
        data = {"server": {"port": 18090}, "open115": section or {}}
        config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return SimpleNamespace(_config=data, config_path=config_path)

    async def test_device_auth_uses_standard_base64_sha256_pkce(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "uid": "uid-1",
                        "time": "123",
                        "sign": "sig",
                        "qrcode": "qr-content",
                    },
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            with patch("services.open115.secrets.token_urlsafe", return_value="fixed-verifier"):
                result = await client.start_device_auth()

        expected = base64.b64encode(hashlib.sha256(b"fixed-verifier").digest()).decode()
        self.assertEqual(result["uid"], "uid-1")
        self.assertEqual(result["qrcode"], "qr-content")
        self.assertEqual(http.calls[0]["kwargs"]["data"]["code_challenge"], expected)
        self.assertNotIn("-", expected)
        self.assertNotIn("_", expected)

    async def test_confirmed_device_auth_persists_tokens_without_returning_them(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {"uid": "uid-1", "time": "123", "sign": "sig", "qrcode": "qr"},
                }),
                response({"state": 1, "data": {"status": 2}}),
                response({
                    "code": 0,
                    "data": {
                        "access_token": "access-secret",
                        "refresh_token": "refresh-secret",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)
            await client.start_device_auth()

            result = await client.poll_device_auth("uid-1")
            stored = yaml.safe_load(cfg.config_path.read_text(encoding="utf-8"))

        self.assertEqual(result, {"status": "confirmed", "bound": True})
        self.assertEqual(stored["open115"]["access_token"], "access-secret")
        self.assertEqual(stored["open115"]["refresh_token"], "refresh-secret")
        self.assertNotIn("access_token", result)
        self.assertNotIn("refresh_token", result)

    async def test_concurrent_refresh_only_calls_refresh_endpoint_once(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "app_id": "app-123",
                "access_token": "old-access",
                "refresh_token": "old-refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "access_token": "new-access",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            results = await asyncio.gather(
                client.refresh_access_token(expected_access_token="old-access"),
                client.refresh_access_token(expected_access_token="old-access"),
            )

        self.assertEqual(results, [True, True])
        refresh_calls = [call for call in http.calls if call["url"].endswith("/open/refreshToken")]
        self.assertEqual(len(refresh_calls), 1)

    async def test_auth_request_retries_once_after_expired_token(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "app_id": "app-123",
                "access_token": "old-access",
                "refresh_token": "old-refresh",
            })
            http = SequenceHTTPClient([
                response({"state": False, "code": 99, "message": "expired"}),
                response({
                    "code": 0,
                    "data": {
                        "access_token": "new-access",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                }),
                response({"state": True, "data": {"user_id": "42"}}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            user = await client.user_info()

        self.assertEqual(user["user_id"], "42")
        self.assertEqual(http.calls[0]["kwargs"]["headers"]["Authorization"], "Bearer old-access")
        self.assertEqual(http.calls[2]["kwargs"]["headers"]["Authorization"], "Bearer new-access")

    async def test_import_refresh_token_refreshes_and_keeps_status_sanitized(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "access_token": "access-secret",
                        "refresh_token": "rotated-secret",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            result = await client.import_refresh_token("imported-secret")
            status = client.status()

        self.assertEqual(result, {"bound": True})
        self.assertTrue(status["bound"])
        self.assertNotIn("access_token", status)
        self.assertNotIn("refresh_token", status)
        self.assertNotIn("imported-secret", repr(status))

    async def test_downurl_forwards_exact_final_player_user_agent(self):
        from services.open115 import Open115Client

        player_ua = "Infuse/8.1 AppleTV"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "state": True,
                    "data": {
                        "123": {
                            "pick_code": "pick",
                            "url": {"url": "https://download.115.test/file?sig=secret"},
                        }
                    },
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            url = await client.downurl("pick", player_ua)

        self.assertEqual(url, "https://download.115.test/file?sig=secret")
        self.assertEqual(http.calls[0]["kwargs"]["headers"]["User-Agent"], player_ua)


if __name__ == "__main__":
    unittest.main()
