"""Route tests for the per-actress film dictionary (P4-1)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.film_dictionary as fd
import services.canonical_resolver as resolver


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(fd.router)
    return TestClient(app)


def test_dictionary_collapses_products_and_counts_owned(client, monkeypatch):
    rows = [
        {"content_id": "umso00533", "dvd_id": "UMSO-533", "service_code": "digital",
         "title_ja": "作品A", "release_date": "2021-08-13", "data_origin": "native", "actress_ids": [7]},
        {"content_id": "h_999umso00533", "dvd_id": "UMSO-533", "service_code": "rental",
         "release_date": "2021-08-13", "data_origin": "native", "actress_ids": [7]},
        {"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital",
         "title_ja": "作品B", "release_date": "2022-01-01", "data_origin": "native", "actress_ids": [7]},
    ]
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {"h_999umso00533"})

    resp = client.get("/api/v1/film-dictionary/actresses/7")
    assert resp.status_code == 200
    body = resp.json()

    assert body["actress_id"] == 7
    assert body["total_films"] == 2           # UMSO-533 (2 products) + ABCD-123
    assert body["owned_films"] == 1           # UMSO-533 owned via its rental member

    by_canon = {f["canonical_number"]: f for f in body["films"]}
    umso = next(f for c, f in by_canon.items() if "UMSO" in c.upper())
    assert umso["member_count"] == 2
    assert umso["owned"] is True
    assert umso["origin"] == "native"
    # Newest release first.
    assert "ABCD" in body["films"][0]["canonical_number"].upper()


def test_supplement_work_is_counted_with_origin(client, monkeypatch):
    rows = [
        {"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital",
         "release_date": "2022-01-01", "data_origin": "native", "actress_ids": [9]},
        {"content_id": None, "dvd_id": "FC2-PPV-998877", "canonical_number": "FC2PPV998877",
         "service_code": "supplement", "data_origin": "supplement", "actress_ids": [9]},
    ]
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: set())

    body = client.get("/api/v1/film-dictionary/actresses/9").json()
    assert body["total_films"] == 2
    supp = next(f for f in body["films"] if f["origin"] == "supplement")
    assert "FC2PPV998877" in supp["canonical_number"].upper().replace("-", "")


def test_no_works_returns_zero(client, monkeypatch):
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: [])
    body = client.get("/api/v1/film-dictionary/actresses/123").json()
    assert body["total_films"] == 0
    assert body["owned_films"] == 0
    assert body["films"] == []


def test_import_db_unavailable_returns_503(client, monkeypatch):
    def boom(aid):
        raise RuntimeError("Could not connect to JavInfo import database")

    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", boom)
    resp = client.get("/api/v1/film-dictionary/actresses/7")
    assert resp.status_code == 503
