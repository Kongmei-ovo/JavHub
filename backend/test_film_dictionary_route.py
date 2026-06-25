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


def test_classify_film_status_tiers():
    assert fd.classify_film_status(True, []) == "owned"
    assert fd.classify_film_status(False, [{"status": "sent"}]) == "in_progress"
    assert fd.classify_film_status(False, [{"status": "candidate", "magnet": "magnet:?xt=1"}]) == "available"
    assert fd.classify_film_status(False, [{"status": "candidate", "magnet": ""}]) == "needs_magnet"
    assert fd.classify_film_status(False, []) == "needs_magnet"


def test_completeness_summary_classifies_gaps(client, monkeypatch):
    rows = [
        {"content_id": "owned00001", "dvd_id": "OWN-001", "service_code": "digital",
         "release_date": "2022-03-01", "data_origin": "native", "actress_ids": [5]},
        {"content_id": "mag00002", "dvd_id": "MAG-002", "service_code": "digital",
         "release_date": "2022-02-01", "data_origin": "native", "actress_ids": [5]},
        {"content_id": "gap00003", "dvd_id": "GAP-003", "service_code": "digital",
         "release_date": "2022-01-01", "data_origin": "native", "actress_ids": [5]},
    ]
    candidates = [
        {"content_id": "mag00002", "dvd_id": "MAG-002", "status": "candidate", "magnet": "magnet:?xt=2"},
        {"content_id": "gap00003", "dvd_id": "GAP-003", "status": "candidate", "magnet": ""},
    ]
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(fd, "_fetch_actress_candidates", lambda aid: candidates)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {"owned00001"})

    body = client.get("/api/v1/film-dictionary/actresses/5/completeness").json()
    assert body["total_films"] == 3
    assert body["owned_films"] == 1
    # owned/in_progress/available/needs_magnet remain; the new owned split keys are additive.
    assert body["summary"]["owned"] == 1
    assert body["summary"]["in_progress"] == 0
    assert body["summary"]["available"] == 1
    assert body["summary"]["needs_magnet"] == 1
    by_canon = {f["canonical_number"]: f["status"] for f in body["films"]}
    assert by_canon[next(c for c in by_canon if "OWN" in c.upper())] == "owned"
    assert by_canon[next(c for c in by_canon if "MAG" in c.upper())] == "available"
    assert by_canon[next(c for c in by_canon if "GAP" in c.upper())] == "needs_magnet"


def test_completeness_adds_metadata_gap_and_cover(client, monkeypatch):
    rows = [
        {"content_id": "full00001", "dvd_id": "FULL-001", "service_code": "digital",
         "release_date": "2022-03-01", "data_origin": "native", "actress_ids": [5]},
        {"content_id": "gap00002", "dvd_id": "GAP-002", "service_code": "digital",
         "release_date": "2022-02-01", "data_origin": "native", "actress_ids": [5]},
    ]
    # member content_id -> rich field row (real DB read lives in _fetch_actress_field_rows)
    fields = {
        "full00001": {"cover_url": "https://x/c1.jpg", "runtime_mins": 120,
                      "maker_name": "M", "label_name": "L", "series_name": "S",
                      "category_names": ["a"]},
        "gap00002": {"cover_url": "", "runtime_mins": None, "maker_name": "",
                     "label_name": "", "series_name": "", "category_names": []},
    }
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(fd, "_fetch_actress_candidates", lambda aid: [])
    monkeypatch.setattr(fd, "_fetch_actress_field_rows", lambda aid: fields)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {"full00001", "gap00002"})

    body = client.get("/api/v1/film-dictionary/actresses/5/completeness").json()
    assert body["summary"]["owned_complete"] == 1
    assert body["summary"]["owned_meta_gap"] == 1
    by = {f["canonical_number"]: f for f in body["films"]}
    full = next(f for c, f in by.items() if "FULL" in c.upper())
    gap = next(f for c, f in by.items() if "GAP" in c.upper())
    assert full["metadata_complete"] is True
    assert full["cover_url"] == "https://x/c1.jpg"
    assert full["metadata_missing"] == []
    assert gap["metadata_complete"] is False
    assert set(gap["metadata_missing"]) == {"cover", "runtime", "maker", "label", "series", "category"}


def test_completeness_emits_funnel_stage_and_summary(client, monkeypatch):
    rows = [
        # owned + complete fields -> complete
        {"content_id": "ok00001", "dvd_id": "OK-001", "service_code": "digital",
         "release_date": "2022-03-01", "data_origin": "native", "actress_ids": [5]},
        # NOT owned but complete fields -> sources stage (needs_magnet, no candidate)
        {"content_id": "src00002", "dvd_id": "SRC-002", "service_code": "digital",
         "release_date": "2022-02-01", "data_origin": "native", "actress_ids": [5]},
        # missing fields (regardless of owned) -> fields stage
        {"content_id": "fld00003", "dvd_id": "FLD-003", "service_code": "digital",
         "release_date": "2022-01-01", "data_origin": "native", "actress_ids": [5]},
    ]
    fields = {
        "ok00001": {"cover_url": "https://x/c.jpg", "runtime_mins": 120, "maker_name": "M",
                    "label_name": "L", "series_name": "S", "category_names": ["a"]},
        "src00002": {"cover_url": "https://x/c.jpg", "runtime_mins": 120, "maker_name": "M",
                     "label_name": "L", "series_name": "S", "category_names": ["a"]},
        "fld00003": {"cover_url": "", "runtime_mins": None, "maker_name": "", "label_name": "",
                     "series_name": "", "category_names": []},
    }
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(fd, "_fetch_actress_candidates", lambda aid: [])
    monkeypatch.setattr(fd, "_fetch_actress_field_rows", lambda aid: fields)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {"ok00001"})
    monkeypatch.setattr(resolver, "codes_in_inventory", lambda codes: set())

    body = client.get("/api/v1/film-dictionary/actresses/5/completeness").json()
    stage = {f["canonical_number"].upper().replace("-", ""): f["funnel_stage"] for f in body["films"]}
    assert stage["OK1"] == "complete"
    assert stage["SRC2"] == "find_source"
    assert stage["FLD3"] == "meta_gap"
    s = body["summary"]
    assert s["total"] == 3
    assert s["owned"] == 1
    assert s["stage_fields"] == 1       # FLD-003
    assert s["stage_sources"] == 1      # SRC-002
    assert s["stage_complete"] == 1     # OK-001


def test_completeness_metadata_complete_decoupled_from_owned(client, monkeypatch):
    # A NOT-owned film with full fields is metadata_complete=True now (was False before).
    rows = [{"content_id": "free00009", "dvd_id": "FREE-009", "service_code": "digital",
             "release_date": "2022-01-01", "data_origin": "native", "actress_ids": [5]}]
    fields = {"free00009": {"cover_url": "https://x/c.jpg", "runtime_mins": 100, "maker_name": "M",
                            "label_name": "L", "series_name": "S", "category_names": ["a"]}}
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(fd, "_fetch_actress_candidates", lambda aid: [])
    monkeypatch.setattr(fd, "_fetch_actress_field_rows", lambda aid: fields)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: set())
    monkeypatch.setattr(resolver, "codes_in_inventory", lambda codes: set())
    body = client.get("/api/v1/film-dictionary/actresses/5/completeness").json()
    film = body["films"][0]
    assert film["metadata_complete"] is True
    assert film["funnel_stage"] == "find_source"


def test_completeness_funnel_maps_acquisition_substatus(client, monkeypatch):
    rows = [
        {"content_id": "dl00001", "dvd_id": "DL-001", "service_code": "digital",
         "release_date": "2022-03-01", "data_origin": "native", "actress_ids": [6]},
        {"content_id": "ft00002", "dvd_id": "FT-002", "service_code": "digital",
         "release_date": "2022-02-01", "data_origin": "native", "actress_ids": [6]},
    ]
    fields = {
        "dl00001": {"cover_url": "https://x/c.jpg", "runtime_mins": 120, "maker_name": "M",
                    "label_name": "L", "series_name": "S", "category_names": ["a"]},
        "ft00002": {"cover_url": "https://x/c.jpg", "runtime_mins": 120, "maker_name": "M",
                    "label_name": "L", "series_name": "S", "category_names": ["a"]},
    }
    candidates = [
        {"content_id": "dl00001", "dvd_id": "DL-001", "status": "candidate", "magnet": "magnet:?xt=1"},
        {"content_id": "ft00002", "dvd_id": "FT-002", "status": "sent", "magnet": ""},
    ]
    monkeypatch.setattr(fd, "_fetch_actress_catalog_rows", lambda aid: rows)
    monkeypatch.setattr(fd, "_fetch_actress_candidates", lambda aid: candidates)
    monkeypatch.setattr(fd, "_fetch_actress_field_rows", lambda aid: fields)
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: set())
    monkeypatch.setattr(resolver, "codes_in_inventory", lambda codes: set())
    body = client.get("/api/v1/film-dictionary/actresses/6/completeness").json()
    stage = {f["canonical_number"].upper().replace("-", ""): f["funnel_stage"] for f in body["films"]}
    assert stage["DL1"] == "downloadable"   # candidate w/ magnet => available => downloadable
    assert stage["FT2"] == "fetching"       # sent => in_progress => fetching
