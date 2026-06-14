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
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.raise_app_exceptions = raise_app_exceptions
        self.default_headers = dict(default_headers or {})

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self.default_headers:
            kwargs["headers"] = {**self.default_headers, **(kwargs.get("headers") or {})}

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


def create_authed_router_test_client(router: Any, **kwargs: Any) -> ASGIClient:
    """Router test client carrying a valid single-user token by default — for
    routers guarded by require_app_token (playback/acquisitions/migration)."""
    from config import config
    from services.emby_auth import issue_token

    token = issue_token(config.emby_compat_username, config.emby_compat_password)
    headers = {"X-Emby-Token": token, **(kwargs.pop("default_headers", None) or {})}
    return create_router_test_client(router, default_headers=headers, **kwargs)


def load_main_app_without_db() -> FastAPI:
    """Import the assembled app without running production database setup."""
    with patch("database.init_db"):
        return importlib.import_module("main").app
