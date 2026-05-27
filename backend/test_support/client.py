from __future__ import annotations

from typing import Any

import anyio
import httpx


class ASGITestClient:
    """Small sync wrapper for isolated FastAPI route tests."""

    def __init__(
        self,
        app: Any,
        *,
        base_url: str = "http://testserver",
        raise_app_exceptions: bool = True,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.raise_app_exceptions = raise_app_exceptions

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(
                app=self.app,
                raise_app_exceptions=self.raise_app_exceptions,
            )
            async with httpx.AsyncClient(
                transport=transport,
                base_url=self.base_url,
            ) as client:
                response = await client.request(method, url, **kwargs)
                await response.aread()
                return response

        return anyio.run(send)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)


def create_test_client(app: Any, **kwargs: Any) -> ASGITestClient:
    return ASGITestClient(app, **kwargs)
