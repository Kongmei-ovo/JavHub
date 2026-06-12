from __future__ import annotations

import unittest
from unittest.mock import patch

from test_support.httpx import FakeHTTPResponse, RecordingAsyncClient
from test_support.postgres import TempPostgresMixin


class DownloaderConfigTests(unittest.TestCase):
    def test_legacy_openlist_is_ignored_and_native_open115_requires_verified_binding(self):
        from services.downloaders import get_downloaders_config

        legacy = {
            "openlist": {"api_url": "http://openlist", "token": "legacy-secret"},
            "open115": {"refresh_token": "refresh", "verified": False, "root_path": "/JavHub"},
            "downloaders": {
                "default_id": "openlist",
                "clients": [{"id": "openlist", "type": "openlist", "address": "http://openlist"}],
            },
        }
        with patch("services.downloaders.config._config", legacy):
            cfg = get_downloaders_config()

        self.assertEqual(cfg["default_id"], "")
        self.assertEqual(cfg["clients"][0]["id"], "open115")
        self.assertEqual(cfg["clients"][0]["type"], "open115")
        self.assertFalse(cfg["clients"][0]["enabled"])
        self.assertNotIn("openlist", {item["value"] for item in cfg["types"]})
        self.assertNotIn("legacy-secret", repr(cfg))

    def test_verified_open115_is_the_default_native_downloader(self):
        from services.downloaders import get_downloaders_config

        with patch("services.downloaders.config._config", {
            "open115": {"refresh_token": "refresh", "verified": True, "root_path": "/JavHub"},
            "downloaders": {"default_id": "open115", "clients": []},
        }):
            cfg = get_downloaders_config()

        self.assertEqual(cfg["default_id"], "open115")
        self.assertTrue(cfg["clients"][0]["enabled"])
        self.assertEqual(cfg["clients"][0]["default_path"], "/JavHub")

    def test_verified_environment_binding_enables_native_open115(self):
        from services.downloaders import get_downloaders_config

        with patch.dict("os.environ", {"OPEN115_REFRESH_TOKEN": "environment-refresh"}), \
            patch("services.downloaders.config._config", {
                "open115": {"verified": True, "root_path": "/JavHub"},
                "downloaders": {"default_id": "open115", "clients": []},
            }):
            cfg = get_downloaders_config()

        self.assertEqual(cfg["default_id"], "open115")
        self.assertTrue(cfg["clients"][0]["enabled"])

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


class DownloaderDuplicateDetectionTests(unittest.TestCase):
    def test_check_duplicate_download_matches_info_hash_and_remote_task_id(self):
        from services.downloaders import check_duplicate_download

        info_hash = "abcdef1234567890abcdef1234567890abcdef12"
        by_hash = check_duplicate_download(
            [{"id": "remote-1", "hash": info_hash.upper(), "status": "downloading"}],
            f"magnet:?xt=urn:btih:{info_hash}",
        )
        by_remote_id = check_duplicate_download(
            [{"id": "gid-123", "hash": "1111111111111111111111111111111111111111"}],
            "magnet:?xt=urn:btih:2222222222222222222222222222222222222222",
            remote_task_id="GID-123",
        )
        clear = check_duplicate_download(
            [{"id": "remote-2", "hash": "3333333333333333333333333333333333333333"}],
            f"magnet:?xt=urn:btih:{info_hash}",
        )

        self.assertFalse(by_hash.success)
        self.assertEqual(by_hash.remote_task_id, "remote-1")
        self.assertIn("duplicate", by_hash.message.lower())
        self.assertFalse(by_remote_id.success)
        self.assertEqual(by_remote_id.remote_task_id, "gid-123")
        self.assertTrue(clear.success)


class DownloaderDuplicateAwareClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_downloader_client_reports_duplicate_before_add_magnet(self):
        from services.downloaders import BaseDownloaderClient, create_downloader_client

        calls = {"add": 0}
        info_hash = "abcdef1234567890abcdef1234567890abcdef12"

        class FakeDownloaderClient(BaseDownloaderClient):
            async def test(self):
                raise AssertionError("not used")

            async def add_magnet(self, magnet, path="", title=""):
                calls["add"] += 1
                raise AssertionError("duplicate should not be submitted")

            async def list_tasks(self):
                return [{"id": "existing-task", "hash": info_hash, "status": "downloading"}]

        with patch("services.downloaders.QBittorrentDownloaderClient", FakeDownloaderClient):
            client = create_downloader_client({"type": "qbittorrent"})
            result = await client.add_magnet(f"magnet:?xt=urn:btih:{info_hash}", "/media", "Title")

        self.assertFalse(result.success)
        self.assertEqual(result.remote_task_id, "existing-task")
        self.assertIn("duplicate", result.message.lower())
        self.assertEqual(calls["add"], 0)

    async def test_create_downloader_client_submits_when_remote_task_listing_empty(self):
        from services.downloaders import BaseDownloaderClient, DownloadActionResult, create_downloader_client

        calls = {"add": 0}

        class FakeDownloaderClient(BaseDownloaderClient):
            async def test(self):
                raise AssertionError("not used")

            async def add_magnet(self, magnet, path="", title=""):
                calls["add"] += 1
                return DownloadActionResult(True, remote_task_id="new-task", message="success")

            async def list_tasks(self):
                return []

        with patch("services.downloaders.QBittorrentDownloaderClient", FakeDownloaderClient):
            client = create_downloader_client({"type": "qbittorrent"})
            result = await client.add_magnet(
                "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
                "/media",
                "Title",
            )

        self.assertTrue(result.success)
        self.assertEqual(result.remote_task_id, "new-task")
        self.assertEqual(calls["add"], 1)


class DownloaderServiceTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
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

    async def test_create_task_reports_duplicate_remote_magnet_without_resubmitting(self):
        from database import get_download_tasks
        from services.downloader import downloader_service
        from services.downloaders import BaseDownloaderClient

        cfg = {
            "id": "qb",
            "type": "qbittorrent",
            "name": "QB",
            "enabled": True,
            "address": "http://qb",
            "default_path": "/downloads",
        }
        info_hash = "abcdef1234567890abcdef1234567890abcdef12"
        calls = {"add": 0}

        class FakeClient(BaseDownloaderClient):
            async def test(self):
                raise AssertionError("not used")

            async def add_magnet(self, magnet, path="", title=""):
                calls["add"] += 1
                raise AssertionError("duplicate should not be submitted")

            async def list_tasks(self):
                return [{"id": "existing-task", "hash": info_hash, "status": "downloading"}]

        with patch("services.downloader.get_downloader_config", return_value=cfg):
            with patch("services.downloaders.QBittorrentDownloaderClient", FakeClient):
                task_id = await downloader_service.create_download_task(
                    "SIVR-438",
                    "Title",
                    f"magnet:?xt=urn:btih:{info_hash}",
                    downloader_id="qb",
                )

        task = get_download_tasks()[0]
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["status"], "failed")
        self.assertIn("duplicate", task["error_msg"].lower())
        self.assertEqual(calls["add"], 0)


class DownloaderClientProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_factory_rejects_retired_openlist_type(self):
        from services.downloaders import create_downloader_client

        with self.assertRaisesRegex(ValueError, "OpenList"):
            create_downloader_client({"type": "openlist"})

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

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse(text="Ok."))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await QBittorrentDownloaderClient(
                {"address": "http://qb", "default_path": "/media", "tags": "javhub"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["url"], "http://qb/api/v2/torrents/add")
        self.assertEqual(post_calls[0]["kwargs"]["data"]["savepath"], "/media")
        self.assertEqual(post_calls[0]["kwargs"]["data"]["tags"], "javhub")

    async def test_qbittorrent_adds_http_torrent_url_to_web_api(self):
        from services.downloaders import QBittorrentDownloaderClient

        torrent_url = "https://indexer.test/download/SIVR-438.torrent"
        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse(text="Ok."))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await QBittorrentDownloaderClient(
                {"address": "http://qb", "default_path": "/media"}
            ).add_magnet(torrent_url)

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["kwargs"]["data"]["urls"], torrent_url)
        self.assertEqual(result.remote_task_id, "")

    async def test_transmission_retries_with_session_id(self):
        from services.downloaders import TransmissionDownloaderClient

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse(status_code=409, headers={"X-Transmission-Session-Id": "sid"}),
        )
        RecordingAsyncClient.add_response(
            "post",
            FakeHTTPResponse({
                "result": "success",
                "arguments": {"torrent-added": {"id": 1, "hashString": "hash", "name": "Title"}},
            }),
        )

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await TransmissionDownloaderClient(
                {"address": "http://tr", "default_path": "/media"}
            ).add_magnet("magnet:?xt=urn:btih:hash")

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["url"], "http://tr/transmission/rpc")
        self.assertEqual(post_calls[1]["kwargs"]["headers"]["X-Transmission-Session-Id"], "sid")
        self.assertEqual(post_calls[1]["kwargs"]["json"]["arguments"]["download-dir"], "/media")

    async def test_deluge_adds_magnet_via_json_rpc(self):
        from services.downloaders import DelugeDownloaderClient

        info_hash = "abcdef1234567890abcdef1234567890abcdef12"
        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"result": True, "error": None}))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"result": info_hash, "error": None}))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"result": True, "error": None}))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await DelugeDownloaderClient(
                {"address": "http://deluge", "password": "pw", "default_path": "/media", "tags": "javhub", "paused": True}
            ).add_magnet(f"magnet:?xt=urn:btih:{info_hash}")

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["url"], "http://deluge/json")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["method"], "auth.login")
        self.assertEqual(post_calls[1]["kwargs"]["json"]["method"], "core.add_torrent_url")
        self.assertEqual(post_calls[1]["kwargs"]["json"]["params"][1]["download_location"], "/media")
        self.assertEqual(post_calls[1]["kwargs"]["json"]["params"][1]["add_paused"], True)
        self.assertEqual(post_calls[2]["kwargs"]["json"]["method"], "label.set_torrent")

    async def test_flood_adds_magnet_to_jesec_endpoint(self):
        from services.downloaders import FloodDownloaderClient

        magnet = "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12"
        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("get", FakeHTTPResponse(status_code=404))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"success": True}))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await FloodDownloaderClient(
                {"address": "http://flood", "default_path": "/media", "tags": "javhub,auto", "paused": True}
            ).add_magnet(magnet)

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["url"], "http://flood/api/torrents/add-urls")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["urls"], [magnet])
        self.assertEqual(post_calls[0]["kwargs"]["json"]["destination"], "/media")
        self.assertEqual(post_calls[0]["kwargs"]["json"]["tags"], ["javhub", "auto"])
        self.assertEqual(post_calls[0]["kwargs"]["json"]["start"], False)

    async def test_rutorrent_adds_magnet_to_addtorrent_php(self):
        from services.downloaders import RuTorrentDownloaderClient

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"result": "Success"}))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await RuTorrentDownloaderClient(
                {"address": "http://rt/rutorrent", "username": "u", "password": "p", "default_path": "/media", "tags": "javhub"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(post_calls[0]["url"], "http://rt/rutorrent/php/addtorrent.php")
        self.assertEqual(post_calls[0]["kwargs"]["data"]["dir_edit"], "/media")
        self.assertEqual(post_calls[0]["kwargs"]["data"]["label"], "javhub")

    async def test_utorrent_fetches_token_then_adds_url(self):
        from services.downloaders import UTorrentDownloaderClient

        RecordingAsyncClient.reset()
        RecordingAsyncClient.add_response("get", FakeHTTPResponse(text="<html><div>token123</div></html>"))
        RecordingAsyncClient.add_response("post", FakeHTTPResponse({"build": 123}))

        with patch("services.downloaders.httpx.AsyncClient", RecordingAsyncClient):
            result = await UTorrentDownloaderClient(
                {"address": "http://ut", "username": "admin", "password": "p", "default_path": "movie\\"}
            ).add_magnet("magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12")

        get_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "get"]
        post_calls = [call for call in RecordingAsyncClient.calls if call["method"] == "post"]
        self.assertTrue(result.success)
        self.assertEqual(get_calls[0]["url"], "http://ut/gui/token.html")
        self.assertEqual(post_calls[0]["url"], "http://ut/gui/")
        self.assertEqual(post_calls[0]["kwargs"]["params"]["token"], "token123")
        self.assertEqual(post_calls[0]["kwargs"]["params"]["action"], "add-url")
        self.assertEqual(post_calls[0]["kwargs"]["params"]["path"], "movie\\")


class DownloaderRouteTests(unittest.TestCase):
    def test_downloaders_route_is_not_captured_by_task_id_route(self):
        from routers.downloads import router
        from test_support.client import create_router_test_client

        with patch(
            "routers.downloads.get_downloaders_config",
            return_value={"default_id": "openlist", "clients": [], "types": []},
        ):
            resp = create_router_test_client(router).get("/api/v1/downloads/downloaders")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["default_id"], "openlist")
