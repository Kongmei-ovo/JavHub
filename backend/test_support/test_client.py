from __future__ import annotations

import warnings

from fastapi import FastAPI
from fastapi import APIRouter

from test_support.client import create_router_test_client, create_test_client


def test_create_test_client_sends_requests_without_httpx_app_shortcut_warning():
    app = FastAPI()

    @app.get("/ok")
    def ok():
        return {"ok": True}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = create_test_client(app).get("/ok")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert not [
        warning for warning in caught
        if "app shortcut is now deprecated" in str(warning.message)
    ]


def test_create_router_test_client_wraps_an_isolated_router():
    router = APIRouter(prefix="/api")

    @router.get("/ok")
    def ok():
        return {"ok": True}

    response = create_router_test_client(router).get("/api/ok")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
