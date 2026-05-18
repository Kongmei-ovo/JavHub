from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TempDbMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.base_patch = patch("database.base.DB_PATH", self.db_path)
        self.base_patch.start()
        from database import init_db

        init_db()

    def tearDown(self):
        self.base_patch.stop()
        self.tmp.cleanup()


class DownloaderConfigTests(unittest.TestCase):
    def test_legacy_openlist_becomes_downloaders_config(self):
        from services.downloaders import get_downloaders_config

        with patch("services.downloaders.config._config", {"openlist": {"api_url": "http://openlist", "default_path": "/115/AV"}}):
            cfg = get_downloaders_config()

        self.assertEqual(cfg["default_id"], "openlist")
        self.assertEqual(cfg["clients"][0]["type"], "openlist")
        self.assertEqual(cfg["clients"][0]["address"], "http://openlist")
        self.assertEqual(cfg["clients"][0]["password"], "")

    def test_blank_secret_preserves_existing_downloader_secret(self):
        from services.downloaders import merge_downloaders_payload

        current = {
            "downloaders": {
                "default_id": "qb",
                "clients": [
                    {
                        "id": "qb",
                        "type": "qbittorrent",
                        "name": "QB",
                        "address": "http://qb",
                        "username": "u",
                        "password": "secret",
                    }
                ],
            }
        }
        incoming = {
            "default_id": "qb",
            "clients": [
                {
                    "id": "qb",
                    "type": "qbittorrent",
                    "name": "QB",
                    "address": "http://qb2",
                    "username": "u",
                    "password": "",
                }
            ],
        }

        with patch("services.downloaders.config._config", current):
            merged = merge_downloaders_payload(incoming)

        self.assertEqual(merged["clients"][0]["password"], "secret")
        self.assertEqual(merged["clients"][0]["address"], "http://qb2")

    def test_config_sanitizer_handles_downloader_lists(self):
        from routers.config import _sanitize_config

        sanitized = _sanitize_config({
            "downloaders": {
                "clients": [
                    {"id": "qb", "password": "secret", "token": "tok", "address": "http://qb"}
                ]
            }
        })

        client = sanitized["downloaders"]["clients"][0]
        self.assertEqual(client["address"], "http://qb")
        self.assertNotIn("password", client)
        self.assertNotIn("token", client)


class DownloaderServiceTests(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_create_task_records_selected_downloader(self):
        from database import get_download_tasks
        from services.downloader import downloader_service
        from services.downloaders import DownloadActionResult

        cfg = {
            "id": "tr",
            "type": "transmission",
            "name": "TR",
            "enabled": True,
            "address": "http://tr",
            "default_path": "/downloads",
        }

        class FakeClient:
            async def add_magnet(self, magnet, path, title):
                return DownloadActionResult(True, remote_task_id="hash123", message="ok")

        with patch("services.downloader.get_downloader_config", return_value=cfg):
            with patch("services.downloader.create_downloader_client", return_value=FakeClient()):
                task_id = await downloader_service.create_download_task(
                    "SIVR-438",
                    "Title",
                    "magnet:?xt=urn:btih:abc",
                    downloader_id="tr",
                )

        task = get_download_tasks()[0]
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["downloader_id"], "tr")
        self.assertEqual(task["downloader_type"], "transmission")
        self.assertEqual(task["remote_task_id"], "hash123")
        self.assertEqual(task["path"], "/downloads")


class DownloaderClientProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_factory_accepts_remaining_pt_depiler_downloaders(self):
        from services.downloaders import (
            DelugeDownloaderClient,
            FloodDownloaderClient,
            RuTorrentDownloaderClient,
            UTorrentDownloaderClient,
            create_downloader_client,
        )

        self.assertIsInstance(create_downloader_client({"type": "deluge"}), DelugeDownloaderClient)
        self.assertIsInstance(create_downloader_client({"type": "flood"}), FloodDownloaderClient)
        self.assertIsInstance(create_downloader_client({"type": "rtorrent"}), RuTorrentDownloaderClient)
        self.assertIsInstance(create_downloader_client({"type": "µTorrent"}), UTorrentDownloaderClient)

    async def test_qbittorrent_adds_magnet_to_web_api(self):
        from services.downloaders import QBittorrentDownloaderClient

        requests = []

        class FakeResponse:
            status_code = 200
            text = "Ok."

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, data=None, **kwargs):
                requests.append((url, data))
                return FakeResponse()

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await QBittorrentDownloaderClient(
                {"address": "http://qb", "default_path": "/media", "tags": "javhub"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        self.assertTrue(result.success)
        self.assertEqual(requests[0][0], "http://qb/api/v2/torrents/add")
        self.assertEqual(requests[0][1]["savepath"], "/media")
        self.assertEqual(requests[0][1]["tags"], "javhub")

    async def test_transmission_retries_with_session_id(self):
        from services.downloaders import TransmissionDownloaderClient

        calls = []

        class FakeResponse:
            def __init__(self, status_code, data=None, headers=None):
                self.status_code = status_code
                self._data = data or {}
                self.headers = headers or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(self.status_code)

            def json(self):
                return self._data

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json=None, headers=None):
                calls.append((url, json, headers or {}))
                if len(calls) == 1:
                    return FakeResponse(409, headers={"X-Transmission-Session-Id": "sid"})
                return FakeResponse(
                    200,
                    {
                        "result": "success",
                        "arguments": {"torrent-added": {"id": 1, "hashString": "hash", "name": "Title"}},
                    },
                )

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await TransmissionDownloaderClient(
                {"address": "http://tr", "default_path": "/media"}
            ).add_magnet("magnet:?xt=urn:btih:hash")

        self.assertTrue(result.success)
        self.assertEqual(calls[0][0], "http://tr/transmission/rpc")
        self.assertEqual(calls[1][2]["X-Transmission-Session-Id"], "sid")
        self.assertEqual(calls[1][1]["arguments"]["download-dir"], "/media")

    async def test_deluge_adds_magnet_via_json_rpc(self):
        from services.downloaders import DelugeDownloaderClient

        requests = []

        class FakeResponse:
            status_code = 200

            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        class FakeClient:
            cookies = {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json=None):
                requests.append((url, json))
                if json["method"] == "auth.login":
                    return FakeResponse({"result": True, "error": None})
                if json["method"] == "core.add_torrent_url":
                    return FakeResponse({"result": "abcdef1234567890abcdef1234567890abcdef12", "error": None})
                return FakeResponse({"result": True, "error": None})

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await DelugeDownloaderClient(
                {"address": "http://deluge", "password": "pw", "default_path": "/media", "tags": "javhub", "paused": True}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        self.assertTrue(result.success)
        self.assertEqual(requests[0][0], "http://deluge/json")
        self.assertEqual(requests[0][1]["method"], "auth.login")
        self.assertEqual(requests[1][1]["method"], "core.add_torrent_url")
        self.assertEqual(requests[1][1]["params"][1]["download_location"], "/media")
        self.assertEqual(requests[1][1]["params"][1]["add_paused"], True)
        self.assertEqual(requests[2][1]["method"], "label.set_torrent")

    async def test_flood_adds_magnet_to_jesec_endpoint(self):
        from services.downloaders import FloodDownloaderClient

        calls = []

        class FakeResponse:
            def __init__(self, status_code=200, data=None, text=""):
                self.status_code = status_code
                self._data = data or {}
                self.text = text

            def json(self):
                return self._data

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url):
                calls.append(("GET", url, None))
                return FakeResponse(404)

            async def request(self, method, url, json=None):
                calls.append((method, url, json))
                return FakeResponse(200, {"success": True})

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await FloodDownloaderClient(
                {"address": "http://flood", "default_path": "/media", "tags": "javhub,auto", "paused": True}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        self.assertTrue(result.success)
        self.assertEqual(calls[1][1], "http://flood/api/torrents/add-urls")
        self.assertEqual(calls[1][2]["urls"], ["magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12"])
        self.assertEqual(calls[1][2]["destination"], "/media")
        self.assertEqual(calls[1][2]["tags"], ["javhub", "auto"])
        self.assertEqual(calls[1][2]["start"], False)

    async def test_rutorrent_adds_magnet_to_addtorrent_php(self):
        from services.downloaders import RuTorrentDownloaderClient

        calls = []

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"result": "Success"}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, method, url, **kwargs):
                calls.append((method, url, kwargs))
                return FakeResponse()

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await RuTorrentDownloaderClient(
                {"address": "http://rt/rutorrent", "username": "u", "password": "p", "default_path": "/media", "tags": "javhub"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        self.assertTrue(result.success)
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "http://rt/rutorrent/php/addtorrent.php")
        self.assertEqual(calls[0][2]["data"]["dir_edit"], "/media")
        self.assertEqual(calls[0][2]["data"]["label"], "javhub")

    async def test_utorrent_fetches_token_then_adds_url(self):
        from services.downloaders import UTorrentDownloaderClient

        calls = []

        class FakeResponse:
            status_code = 200
            text = "<html><div>token123</div></html>"

            def raise_for_status(self):
                return None

            def json(self):
                return {"build": 123}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, params=None):
                calls.append(("GET", url, params))
                return FakeResponse()

            async def request(self, method, url, params=None):
                calls.append((method, url, params))
                return FakeResponse()

        with patch("services.downloaders.httpx.AsyncClient", return_value=FakeClient()):
            result = await UTorrentDownloaderClient(
                {"address": "http://ut", "username": "admin", "password": "p", "default_path": "movie\\"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        self.assertTrue(result.success)
        self.assertEqual(calls[0][1], "http://ut/gui/token.html")
        self.assertEqual(calls[1][1], "http://ut/gui/")
        self.assertEqual(calls[1][2]["token"], "token123")
        self.assertEqual(calls[1][2]["action"], "add-url")
        self.assertEqual(calls[1][2]["path"], "movie\\")


class DownloaderRouteTests(unittest.TestCase):
    def test_downloaders_route_is_not_captured_by_task_id_route(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.downloads import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "routers.downloads.get_downloaders_config",
            return_value={"default_id": "openlist", "clients": [], "types": []},
        ):
            resp = TestClient(app).get("/api/v1/downloads/downloaders")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["default_id"], "openlist")
