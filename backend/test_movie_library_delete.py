"""Tests for whole-folder library delete (P4-2 delete interface)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.movie_resources as mr
from services.open115_downloader import Open115DownloaderClient, encode_movie_directory


class _FakeClient:
    root_path = "/JavHub"

    def __init__(self):
        self.ensured = None
        self.deleted = []

    async def ensure_folder_path(self, path):
        self.ensured = path
        return "folder-123"

    async def delete_files(self, file_ids, parent_id=None):
        self.deleted.append((list(file_ids), parent_id))


def test_delete_movie_directory_removes_whole_folder():
    client = _FakeClient()
    dl = Open115DownloaderClient(client)
    result = asyncio.run(dl.delete_movie_directory("UMSO533"))

    assert client.ensured == f"/JavHub/{encode_movie_directory('UMSO533')}"
    assert client.deleted == [(["folder-123"], None)]
    assert result["folder_id"] == "folder-123"


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(mr.router)
    return TestClient(app)


def test_delete_library_purges_resources_and_folder(client, monkeypatch):
    calls = {}

    async def fake_delete_dir(movie_id):
        calls["folder"] = movie_id
        return {"folder_id": "f1", "path": "/JavHub/x"}

    monkeypatch.setattr(mr, "resolve_canonical_code", lambda code: "UMSO533")
    monkeypatch.setattr(mr, "list_movie_resources", lambda mid: [{"id": 1}] if mid == "UMSO533" else [])
    monkeypatch.setattr(mr, "delete_all_movie_resources", lambda mid: [{"id": 1}, {"id": 2}] if mid == "UMSO533" else [])
    monkeypatch.setattr(mr.open115_downloader, "delete_movie_directory", fake_delete_dir)

    resp = client.request("DELETE", "/api/v1/movies/umso00533/library")
    assert resp.status_code == 200
    body = resp.json()
    assert body["movie_id"] == "UMSO533"
    assert body["purged_resources"] == 2
    assert body["folder_deleted"] is True
    assert calls["folder"] == "UMSO533"


def test_delete_library_falls_back_to_legacy_key(client, monkeypatch):
    # No resources under the canonical key -> use the raw (legacy content_id) key.
    monkeypatch.setattr(mr, "resolve_canonical_code", lambda code: "UMSO533")
    monkeypatch.setattr(mr, "list_movie_resources", lambda mid: [])
    seen = {}
    monkeypatch.setattr(mr, "delete_all_movie_resources", lambda mid: seen.setdefault("key", mid) or [])

    async def fake_delete_dir(movie_id):
        seen["folder_key"] = movie_id
        return {"folder_id": "f", "path": "p"}

    monkeypatch.setattr(mr.open115_downloader, "delete_movie_directory", fake_delete_dir)

    resp = client.request("DELETE", "/api/v1/movies/legacycid001/library")
    assert resp.status_code == 200
    assert seen["key"] == "legacycid001"
    assert seen["folder_key"] == "legacycid001"


def test_delete_library_reports_when_115_fails(client, monkeypatch):
    monkeypatch.setattr(mr, "resolve_canonical_code", lambda code: "ABC123")
    monkeypatch.setattr(mr, "list_movie_resources", lambda mid: [{"id": 1}])
    monkeypatch.setattr(mr, "delete_all_movie_resources", lambda mid: [{"id": 1}])

    async def boom(movie_id):
        raise RuntimeError("115 down")

    monkeypatch.setattr(mr.open115_downloader, "delete_movie_directory", boom)

    body = client.request("DELETE", "/api/v1/movies/ABC-123/library").json()
    # Resources still purged locally; folder delete reported as failed.
    assert body["purged_resources"] == 1
    assert body["folder_deleted"] is False
