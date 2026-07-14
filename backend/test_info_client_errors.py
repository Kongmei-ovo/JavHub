from __future__ import annotations

import unittest
import httpx

from modules.info_client import InfoClient


class _FakeHttpClient:
    def __init__(self, *, response: httpx.Response | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.is_closed = False

    async def aclose(self) -> None:
        self.is_closed = True

    async def get(self, *_args, **_kwargs) -> httpx.Response:
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response

    async def post(self, *_args, **_kwargs) -> httpx.Response:
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def _response(status_code: int, path: str, *, json_body=None, text: str | None = None) -> httpx.Response:
    request = httpx.Request("GET", f"http://javinfo.test{path}")
    if json_body is not None:
        return httpx.Response(status_code, request=request, json=json_body)
    return httpx.Response(status_code, request=request, text=text or "")


class InfoClientErrorMappingTest(unittest.IsolatedAsyncioTestCase):
    async def _capture(self, client: InfoClient, method_name: str, *args, fake_http: _FakeHttpClient, **kwargs) -> Exception:
        configured = InfoClient(
            api_url=client.api_url,
            timeout=client.timeout,
            client_factory=lambda: fake_http,
        )
        try:
            with self.assertRaises(Exception) as ctx:
                await getattr(configured, method_name)(*args, **kwargs)
        finally:
            await configured.close()
        return ctx.exception

    def _assert_javinfo_error(
        self,
        exc: Exception,
        class_name: str,
        *,
        endpoint_path: str,
        status_code: int | None,
        message_contains: str,
    ) -> None:
        self.assertEqual(type(exc).__name__, class_name)
        self.assertEqual(getattr(exc, "endpoint_path", None), endpoint_path)
        self.assertEqual(getattr(exc, "status_code", None), status_code)
        upstream_message = getattr(exc, "upstream_message", "")
        self.assertIn(message_contains, upstream_message)
        self.assertLessEqual(len(upstream_message), 200)
        self.assertIn(endpoint_path, str(exc))

    async def test_get_maps_request_errors_to_unavailable_with_endpoint_path(self):
        path = "/api/v1/stats"
        request = httpx.Request("GET", f"http://javinfo.test{path}")
        cases = (
            httpx.ReadTimeout("timed out", request=request),
            httpx.ConnectError("connection refused", request=request),
        )
        for error in cases:
            with self.subTest(error=error.__class__.__name__):
                client = InfoClient(api_url="http://javinfo.test")
                fake_http = _FakeHttpClient(error=error)

                exc = await self._capture(client, "_get", path, fake_http=fake_http)

                self._assert_javinfo_error(
                    exc,
                    "JavInfoUnavailable",
                    endpoint_path=path,
                    status_code=None,
                    message_contains=str(error),
                )

    async def test_proxy_get_maps_auth_statuses_to_auth_error(self):
        path = "/api/v1/supplement/stats"
        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                client = InfoClient(api_url="http://javinfo.test")
                fake_http = _FakeHttpClient(
                    response=_response(status_code, path, json_body={"detail": "invalid supplement token"})
                )

                exc = await self._capture(client, "proxy_get", path, fake_http=fake_http)

                self._assert_javinfo_error(
                    exc,
                    "JavInfoAuthError",
                    endpoint_path=path,
                    status_code=status_code,
                    message_contains="invalid supplement token",
                )

    async def test_get_maps_404_to_not_found(self):
        path = "/api/v1/videos/miaa999"
        client = InfoClient(api_url="http://javinfo.test")
        fake_http = _FakeHttpClient(response=_response(404, path, json_body={"error": "video not found"}))

        exc = await self._capture(client, "_get", path, fake_http=fake_http)

        self._assert_javinfo_error(
            exc,
            "JavInfoNotFound",
            endpoint_path=path,
            status_code=404,
            message_contains="video not found",
        )

    async def test_proxy_post_maps_500_json_error_payload_to_bad_gateway(self):
        path = "/api/v1/supplement/movies/detail/jobs"
        client = InfoClient(api_url="http://javinfo.test")
        fake_http = _FakeHttpClient(response=_response(500, path, json_body={"message": "database unavailable"}))

        exc = await self._capture(client, "proxy_post", path, fake_http=fake_http)

        self._assert_javinfo_error(
            exc,
            "JavInfoBadGateway",
            endpoint_path=path,
            status_code=500,
            message_contains="database unavailable",
        )

    async def test_get_list_maps_non_json_error_payload_to_bad_gateway(self):
        path = "/api/v1/makers"
        long_text = "upstream html failure " * 30
        client = InfoClient(api_url="http://javinfo.test")
        fake_http = _FakeHttpClient(response=_response(502, path, text=long_text))

        exc = await self._capture(client, "_get_list", path, fake_http=fake_http)

        self._assert_javinfo_error(
            exc,
            "JavInfoBadGateway",
            endpoint_path=path,
            status_code=502,
            message_contains="upstream html failure",
        )

    async def test_get_maps_success_non_json_payload_to_contract_error(self):
        path = "/api/v1/stats"
        client = InfoClient(api_url="http://javinfo.test")
        fake_http = _FakeHttpClient(response=_response(200, path, text="<html>not json</html>"))

        exc = await self._capture(client, "_get", path, fake_http=fake_http)

        self._assert_javinfo_error(
            exc,
            "JavInfoContractError",
            endpoint_path=path,
            status_code=200,
            message_contains="not json",
        )


if __name__ == "__main__":
    unittest.main()
