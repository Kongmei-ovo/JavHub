from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import patch

import anyio
import httpx
from fastapi import FastAPI


class ASGIClient:
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


def create_test_client(app: Any, **kwargs: Any) -> ASGIClient:
    return ASGIClient(app, **kwargs)


def create_router_test_client(router: Any, **kwargs: Any) -> ASGIClient:
    app = FastAPI()
    app.include_router(router)
    return create_test_client(app, **kwargs)


def load_main_app_without_db() -> FastAPI:
    """Import the assembled app without running production database setup."""
    with patch("database.init_db"):
        return importlib.import_module("main").app
