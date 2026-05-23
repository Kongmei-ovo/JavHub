from __future__ import annotations

import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException

from middlewares.rate_limit import RateLimiter
from routers import stream
from routers.config import _mask_url_credentials, test_telegram as run_telegram_test


class StreamSecurityTests(unittest.TestCase):
    def test_rejects_private_literal_and_ipv6_loopback(self):
        for url in ("https://127.0.0.1/playlist.m3u8", "https://[::1]/playlist.m3u8"):
            with self.subTest(url=url):
                with self.assertRaises(HTTPException):
                    stream._validate_proxy_url(url)

    def test_rejects_non_whitelisted_domain_before_fetch(self):
        with self.assertRaises(HTTPException):
            stream._validate_proxy_url("https://attacker.example/playlist.m3u8")

    def test_rejects_whitelisted_domain_that_resolves_private(self):
        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("127.0.0.1", 443)),
        ]):
            with self.assertRaises(HTTPException):
                stream._validate_proxy_url("https://video.jable.tv/playlist.m3u8")

    def test_allows_whitelisted_public_domain_and_subdomain(self):
        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("93.184.216.34", 443)),
        ]):
            self.assertEqual(
                stream._validate_proxy_url("https://cdn.jable.tv/playlist.m3u8"),
                "https://cdn.jable.tv/playlist.m3u8",
            )

    def test_allows_jable_cdn_domain_used_by_hls_playlist(self):
        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("93.184.216.34", 443)),
        ]):
            self.assertEqual(
                stream._validate_proxy_url("https://fuaf-uying.mushroomtrack.com/hls/playlist.m3u8"),
                "https://fuaf-uying.mushroomtrack.com/hls/playlist.m3u8",
            )

    def test_allows_hohoj_media_domain_used_by_hls_playlist(self):
        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("93.184.216.34", 443)),
        ]):
            self.assertEqual(
                stream._validate_proxy_url("https://video-5.ggjav.com/video/index.m3u8"),
                "https://video-5.ggjav.com/video/index.m3u8",
            )

    def test_allows_whitelisted_domain_resolving_to_proxy_fake_ip(self):
        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("198.18.0.81", 443)),
        ]):
            self.assertEqual(
                stream._validate_proxy_url("https://fuaf-uying.mushroomtrack.com/hls/playlist.m3u8"),
                "https://fuaf-uying.mushroomtrack.com/hls/playlist.m3u8",
            )

    def test_uses_source_referer_for_protected_hls_hosts(self):
        self.assertEqual(
            stream._referer_for_stream_url("https://surrit.com/video/index.m3u8"),
            "https://missav.ai/",
        )
        self.assertEqual(
            stream._referer_for_stream_url("https://video-5.ggjav.com/video/index.m3u8"),
            "https://hohoj.tv/",
        )


class StreamRedirectSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_target_is_validated(self):
        request = httpx.Request("GET", "https://cdn.jable.tv/playlist.m3u8")
        response = httpx.Response(
            302,
            headers={"location": "https://attacker.example/private.m3u8"},
            request=request,
        )
        client = AsyncMock()
        client.get.return_value = response

        with patch("routers.stream.socket.getaddrinfo", return_value=[
            (0, 0, 0, "", ("93.184.216.34", 443)),
        ]):
            with self.assertRaises(HTTPException):
                await stream._fetch_validated_url(client, "https://cdn.jable.tv/playlist.m3u8", {})


class HardeningRegressionTests(unittest.TestCase):
    def test_url_masking_removes_proxy_credentials(self):
        self.assertEqual(
            _mask_url_credentials("http://user:pass@example.com:8080"),
            "http://example.com:8080",
        )
        self.assertEqual(_mask_url_credentials("http://example.com:8080"), "http://example.com:8080")

    def test_rate_limiter_uses_burst_capacity_and_refill(self):
        limiter = RateLimiter(requests_per_minute=60, burst=2)
        self.assertTrue(limiter.is_allowed("client")[0])
        self.assertTrue(limiter.is_allowed("client")[0])
        allowed, headers = limiter.is_allowed("client")
        self.assertFalse(allowed)
        self.assertIn("Retry-After", headers)

        tokens, _ = __import__("middlewares.rate_limit").rate_limit._rate_limit_data["client"]
        __import__("middlewares.rate_limit").rate_limit._rate_limit_data["client"] = (tokens, time.time() - 1.1)
        self.assertTrue(limiter.is_allowed("client")[0])

    def test_translation_count_parameterizes_mapping_type(self):
        from database import translation

        executed = {}

        class Cursor:
            def execute(self, sql, params=None):
                executed["sql"] = sql
                executed["params"] = params

            def fetchall(self):
                return []

        class Conn:
            def cursor(self):
                return Cursor()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("database.translation.get_db", return_value=Conn()):
            self.assertEqual(translation.get_translation_count("category"), 0)

        self.assertIn("LIKE ?", executed["sql"])
        self.assertEqual(executed["params"], ("category:%",))


class TelegramConfigSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_telegram_test_rejects_path_delimiters_before_http_request(self):
        with patch("routers.config.config._config", {"telegram": {"allowed_user_ids": [123456]}}), \
             patch("httpx.AsyncClient") as async_client:
            result = await run_telegram_test("123456:bad/token")

        self.assertFalse(result["success"])
        self.assertIn("Token", result["error"])
        async_client.assert_not_called()


class SourceRegistryTests(unittest.TestCase):
    def test_registry_skips_explicitly_unimplemented_sources(self):
        from sources.registry import SourceRegistry

        class Unimplemented:
            name = "stub"

            def is_implemented(self):
                return False

        with patch.object(SourceRegistry, "_sources", {}), patch.object(SourceRegistry, "_priority", []):
            SourceRegistry.register(Unimplemented())
            self.assertIsNone(SourceRegistry.get("stub"))
            self.assertEqual(SourceRegistry.priority(), [])


class InfoClientPatchAuthTest(unittest.IsolatedAsyncioTestCase):
    async def test_proxy_patch_injects_bearer_token(self):
        from modules.info_client import InfoClient

        client = InfoClient()
        with patch.dict("os.environ", {"SUPPLEMENT_ADMIN_TOKEN": "my-secret"}, clear=False), \
             patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_client.patch.return_value = mock_response
            get_client.return_value = mock_client

            await client.proxy_patch("/api/v1/config", {"proxy_url": "http://proxy"})

        headers = mock_client.patch.call_args.kwargs.get("headers", {})
        self.assertEqual(headers.get("Authorization"), "Bearer my-secret")


if __name__ == "__main__":
    unittest.main()
