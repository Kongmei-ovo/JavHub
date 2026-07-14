from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from routers.source_management import router
from services.source_manager import SourceConfigError
from test_support.client import create_test_client


app = FastAPI()
app.include_router(router)
client = create_test_client(app)


def _payload(**overrides):
    payload = {
        "type": "torznab",
        "name": "",
        "kind": "prowlarr",
        "enabled": False,
        "base_url": "",
        "api_key": "",
        "indexer": "all",
        "categories": "",
        "limit": 20,
        "timeout": 15,
    }
    payload.update(overrides)
    return payload


def test_source_config_returns_service_snapshot_unchanged():
    snapshot = {
        "builtins": [{"id": "m3u8"}],
        "sources": [{"id": "source-1"}],
        "types": ["torznab", "avdb"],
    }

    with patch(
        "routers.source_management.get_source_snapshot",
        return_value=snapshot,
    ) as get_snapshot:
        response = client.get("/api/v1/sources/config")

    assert response.status_code == 200
    assert response.json() == snapshot
    get_snapshot.assert_called_once_with()


@pytest.mark.parametrize(
    ("request_body", "expected_payload", "snapshot"),
    [
        (
            {
                "type": "torznab",
                "name": "Prowlarr",
                "kind": "prowlarr",
                "base_url": "http://prowlarr.test",
                "api_key": "secret",
            },
            _payload(
                name="Prowlarr",
                base_url="http://prowlarr.test",
                api_key="secret",
            ),
            {"sources": [{"id": "prowlarr-id"}]},
        ),
        (
            {"type": "avdb"},
            _payload(type="avdb"),
            {"sources": [{"id": "avdb"}]},
        ),
    ],
)
def test_create_source_passes_validated_payload_and_returns_snapshot(
    request_body,
    expected_payload,
    snapshot,
):
    with patch(
        "routers.source_management.create_source",
        return_value=snapshot,
    ) as create:
        response = client.post("/api/v1/sources", json=request_body)

    assert response.status_code == 200
    assert response.json() == snapshot
    create.assert_called_once_with(expected_payload)


def test_update_source_passes_id_and_validated_payload_and_returns_snapshot():
    snapshot = {"sources": [{"id": "jackett-id", "enabled": True}]}
    request_body = {
        "type": "torznab",
        "name": "Jackett",
        "kind": "jackett",
        "enabled": True,
        "base_url": "https://jackett.test",
        "api_key": "rotated-secret",
        "indexer": "all",
        "categories": "2000,5000",
        "limit": 50,
        "timeout": 30,
    }

    with patch(
        "routers.source_management.update_source",
        return_value=snapshot,
    ) as update:
        response = client.put("/api/v1/sources/jackett-id", json=request_body)

    assert response.status_code == 200
    assert response.json() == snapshot
    update.assert_called_once_with("jackett-id", request_body)


def test_delete_source_passes_id_and_returns_snapshot():
    snapshot = {"sources": []}

    with patch(
        "routers.source_management.delete_source",
        return_value=snapshot,
    ) as delete:
        response = client.delete("/api/v1/sources/obsolete-id")

    assert response.status_code == 200
    assert response.json() == snapshot
    delete.assert_called_once_with("obsolete-id")


@pytest.mark.parametrize(
    ("method", "path", "body", "service_name", "status_code", "message"),
    [
        (
            "post",
            "/api/v1/sources",
            {"type": "avdb"},
            "create_source",
            409,
            "AVDB 来源已存在",
        ),
        (
            "put",
            "/api/v1/sources/missing-id",
            {"type": "torznab"},
            "update_source",
            404,
            "来源不存在",
        ),
        (
            "delete",
            "/api/v1/sources/invalid-id",
            None,
            "delete_source",
            400,
            "来源无法删除",
        ),
    ],
)
def test_source_config_errors_preserve_exact_status_and_message(
    method,
    path,
    body,
    service_name,
    status_code,
    message,
):
    with patch(
        f"routers.source_management.{service_name}",
        side_effect=SourceConfigError(message, status_code=status_code),
    ):
        response = getattr(client, method)(path, json=body) if body else getattr(
            client, method
        )(path)

    assert response.status_code == status_code
    assert response.json() == {"detail": message}


def test_unexpected_service_error_is_not_swallowed():
    with patch(
        "routers.source_management.create_source",
        side_effect=RuntimeError("write failed"),
    ), pytest.raises(RuntimeError, match="write failed"):
        client.post("/api/v1/sources", json={"type": "avdb"})


@pytest.mark.parametrize(
    "request_body",
    [
        {"type": "rss"},
        {"type": "torznab", "kind": "rss"},
        {"type": "torznab", "limit": 0},
        {"type": "torznab", "limit": 101},
        {"type": "torznab", "timeout": 0},
        {"type": "torznab", "timeout": 61},
    ],
)
def test_invalid_source_payload_is_rejected_before_service_call(request_body):
    with patch("routers.source_management.create_source") as create:
        response = client.post("/api/v1/sources", json=request_body)

    assert response.status_code == 422
    create.assert_not_called()


@pytest.mark.parametrize(
    ("method", "path", "request_body", "service_name"),
    [
        (
            "post",
            "/api/v1/sources",
            {"type": "torznab", "base_urll": "https://typo.test"},
            "create_source",
        ),
        (
            "put",
            "/api/v1/sources/source-id",
            {"type": "torznab", "categorie": "5000"},
            "update_source",
        ),
    ],
)
def test_unknown_source_payload_field_is_rejected_before_service_call(
    method,
    path,
    request_body,
    service_name,
):
    with patch(
        f"routers.source_management.{service_name}",
        return_value={"sources": []},
    ) as service:
        response = getattr(client, method)(path, json=request_body)

    assert response.status_code == 422
    service.assert_not_called()


def test_search_sources_defaults_to_auto_and_passes_keyword_as_dvd_id():
    result = {
        "items": [{"magnet": "magnet:?xt=urn:btih:AUTO"}],
        "attempts": [{"source": "one", "ok": True}],
        "errors": [],
    }
    search = AsyncMock(return_value=result)

    with patch(
        "routers.source_management.search_magnets_for_item",
        new=search,
        create=True,
    ):
        response = client.post(
            "/api/v1/sources/search",
            json={"keyword": "MIAA-784"},
        )

    assert response.status_code == 200
    assert response.json() == result
    search.assert_awaited_once_with({"dvd_id": "MIAA-784"}, source_names=None)


def test_search_sources_resolves_and_calls_only_selected_runtime_source():
    result = {"items": [], "attempts": [], "errors": []}
    search = AsyncMock(return_value=result)

    with patch(
        "routers.source_management.source_runtime_name",
        return_value="My Prowlarr",
        create=True,
    ) as runtime_name, patch(
        "routers.source_management.search_magnets_for_item",
        new=search,
        create=True,
    ):
        response = client.post(
            "/api/v1/sources/search",
            json={"keyword": "MIAA-784", "source_id": "source-id"},
        )

    assert response.status_code == 200
    runtime_name.assert_called_once_with("source-id")
    search.assert_awaited_once_with(
        {"dvd_id": "MIAA-784"},
        source_names=["My Prowlarr"],
    )


def test_search_sources_returns_404_for_missing_or_disabled_source():
    search = AsyncMock()

    with patch(
        "routers.source_management.source_runtime_name",
        return_value=None,
        create=True,
    ), patch(
        "routers.source_management.search_magnets_for_item",
        new=search,
        create=True,
    ):
        response = client.post(
            "/api/v1/sources/search",
            json={"keyword": "MIAA-784", "source_id": "disabled-id"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "下载源不存在或未启用"}
    search.assert_not_awaited()


def test_search_route_redacts_secrets_from_attempt_errors_before_response():
    leaked = (
        "api-secret",
        "pass-secret",
        "bearer-secret",
        "cookie-secret",
        "url-user",
        "url-password",
    )
    error = "\n".join(
        [
            "jackett_apikey=api-secret passkey=pass-secret",
            "Authorization: Bearer bearer-secret",
            "Cookie: sid=cookie-secret; Path=/",
            (
                "GET https://url-user:url-password@indexer.test/api"
                "?token=query-secret"
            ),
        ]
    )
    result = {
        "items": [],
        "attempts": [{"source": "jackett", "ok": False, "error": error}],
        "errors": [{"source": "jackett", "ok": False, "error": error}],
        "best": None,
        "candidates": [],
        "alternatives": [],
    }

    with patch(
        "routers.source_management.search_magnets_for_item",
        new=AsyncMock(return_value=result),
    ):
        response = client.post(
            "/api/v1/sources/search",
            json={"keyword": "MIAA-784"},
        )

    assert response.status_code == 200
    serialized = response.text
    for secret in (*leaked, "query-secret"):
        assert secret not in serialized


@pytest.mark.parametrize(
    "request_body",
    [
        {"keyword": ""},
        {"keyword": "A" * 129},
        {"keyword": "MIAA-784", "unexpected": True},
    ],
)
def test_search_sources_rejects_invalid_or_extra_fields(request_body):
    search = AsyncMock()

    with patch(
        "routers.source_management.search_magnets_for_item",
        new=search,
        create=True,
    ):
        response = client.post("/api/v1/sources/search", json=request_body)

    assert response.status_code == 422
    search.assert_not_awaited()
