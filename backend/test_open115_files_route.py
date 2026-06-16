from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import yaml

from test_open115 import SequenceHTTPClient, response
from test_support.client import create_router_test_client


def _file(**kwargs):
    from services.open115 import Open115File

    base = dict(
        file_id="1",
        parent_id="0",
        name="x",
        pick_code="pc",
        is_dir=False,
        size=0,
        duration=0,
        extension="",
    )
    base.update(kwargs)
    return Open115File(**base)


class Open115FilesRouteTests(unittest.TestCase):
    def _client(self):
        from routers.open115_files import router

        return create_router_test_client(router)

    def test_list_returns_files_breadcrumb_and_count(self):
        client = AsyncMock()
        client.list_folder.return_value = {
            "files": [_file(file_id="10", name="dir", is_dir=True), _file(file_id="11", name="a.mp4", extension="mp4")],
            "path": [{"file_id": "0", "name": "根目录"}, {"file_id": "10", "name": "dir"}],
            "count": 2,
        }
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().get("/api/v1/open115/files?cid=10&limit=50")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual([f["file_id"] for f in body["files"]], ["10", "11"])
        self.assertEqual(body["path"][-1]["name"], "dir")
        self.assertEqual(body["count"], 2)
        client.list_folder.assert_awaited_once_with("10", offset=0, limit=50)

    def test_keyword_routes_to_search(self):
        client = AsyncMock()
        client.search_files.return_value = [_file(file_id="9", name="hit.mp4", extension="mp4")]
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().get("/api/v1/open115/files?cid=0&keyword=hit")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["keyword"], "hit")
        self.assertEqual(body["path"], [])
        self.assertEqual([f["file_id"] for f in body["files"]], ["9"])
        client.search_files.assert_awaited_once_with("hit", cid="0", offset=0, limit=100)
        client.list_folder.assert_not_awaited()

    def test_unbound_maps_to_409_with_code(self):
        from services.open115 import Open115AuthRequired

        client = AsyncMock()
        client.list_folder.side_effect = Open115AuthRequired(None, "115 尚未绑定")
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().get("/api/v1/open115/files")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "open115_unbound")

    def test_protocol_error_maps_to_502(self):
        from services.open115 import Open115Error

        client = AsyncMock()
        client.list_folder.side_effect = Open115Error(40100, "配额不足")
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().get("/api/v1/open115/files")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "配额不足")

    def test_move_passes_ids_and_target(self):
        client = AsyncMock()
        client.move_files.return_value = 3
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().post(
                "/api/v1/open115/files/move",
                json={"file_ids": ["1", "2", "3"], "to_cid": "99"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True, "moved": 3})
        client.move_files.assert_awaited_once_with(["1", "2", "3"], "99")

    def test_copy_passes_ids_and_target(self):
        client = AsyncMock()
        client.copy_files.return_value = 2
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().post(
                "/api/v1/open115/files/copy",
                json={"file_ids": ["1", "2"], "to_cid": "5"},
            )
        self.assertEqual(resp.json(), {"ok": True, "copied": 2})
        client.copy_files.assert_awaited_once_with(["1", "2"], "5")

    def test_rename_passes_args(self):
        client = AsyncMock()
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().post(
                "/api/v1/open115/files/rename",
                json={"file_id": "7", "name": "新名字.mp4"},
            )
        self.assertEqual(resp.json(), {"ok": True})
        client.rename_file.assert_awaited_once_with("7", "新名字.mp4")

    def test_delete_passes_ids(self):
        client = AsyncMock()
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().post(
                "/api/v1/open115/files/delete",
                json={"file_ids": ["1", "2"], "parent_id": "0"},
            )
        self.assertEqual(resp.json(), {"ok": True})
        client.delete_files.assert_awaited_once_with(["1", "2"], "0")

    def test_video_sources_from_transcode_urls(self):
        from services.open115 import TranscodeURL

        client = AsyncMock()
        client.video_transcode_urls.return_value = [
            TranscodeURL(url="https://hls/1.m3u8", definition=4, desc="超清"),
            TranscodeURL(url="https://hls/2.m3u8", definition=2, desc="高清"),
        ]
        with patch("routers.open115_files.open115_client", client):
            resp = self._client().get("/api/v1/open115/files/video?pick_code=pc1")
        self.assertEqual(resp.status_code, 200)
        sources = resp.json()["sources"]
        self.assertEqual([s["definition"] for s in sources], [4, 2])
        client.video_transcode_urls.assert_awaited_once_with("pc1")


class Open115ClientFileMethodTests(unittest.IsolatedAsyncioTestCase):
    def _config(self, root: Path) -> SimpleNamespace:
        config_path = root / "config.yaml"
        data = {"server": {"port": 18090}, "open115": {"app_id": "app", "access_token": "tok"}}
        config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return SimpleNamespace(_config=data, config_path=config_path)

    async def _make(self, tmp: str, http: SequenceHTTPClient):
        from services.open115 import Open115Client

        return Open115Client(config_obj=self._config(Path(tmp)), http_client=http, min_request_interval=0)

    async def test_rename_hits_update_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([response({"state": 1, "data": {}})])
            client = await self._make(tmp, http)
            await client.rename_file("123", "new.mp4")
        call = http.calls[0]
        self.assertTrue(call["url"].endswith("/open/ufile/update"))
        self.assertEqual(call["kwargs"]["data"], {"file_id": "123", "file_name": "new.mp4"})

    async def test_move_joins_ids_and_returns_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([response({"state": 1, "data": {}})])
            client = await self._make(tmp, http)
            moved = await client.move_files(["1", "2", "3"], "99")
        self.assertEqual(moved, 3)
        call = http.calls[0]
        self.assertTrue(call["url"].endswith("/open/ufile/move"))
        self.assertEqual(call["kwargs"]["data"], {"file_ids": "1,2,3", "to_cid": "99"})

    async def test_copy_uses_file_id_and_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([response({"state": 1, "data": {}})])
            client = await self._make(tmp, http)
            copied = await client.copy_files(["4", "5"], "7")
        self.assertEqual(copied, 2)
        call = http.calls[0]
        self.assertTrue(call["url"].endswith("/open/ufile/copy"))
        self.assertEqual(call["kwargs"]["data"], {"file_id": "4,5", "pid": "7"})

    async def test_search_passes_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([response({"state": 1, "data": [{"fid": "8", "fn": "hit.mp4"}]})])
            client = await self._make(tmp, http)
            files = await client.search_files("hit", cid="0", limit=20)
        self.assertEqual([f.file_id for f in files], ["8"])
        call = http.calls[0]
        self.assertTrue(call["url"].endswith("/open/ufile/search"))
        self.assertEqual(call["kwargs"]["params"]["search_value"], "hit")

    async def test_list_folder_returns_files_path_count(self):
        payload = {
            "state": 1,
            "count": 2,
            "data": [{"fid": "10", "fn": "dir", "fc": "0"}, {"fid": "11", "fn": "a.mp4"}],
            "path": [{"cid": "0", "name": "根目录"}, {"cid": "10", "name": "dir"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([response(payload)])
            client = await self._make(tmp, http)
            result = await client.list_folder("10", limit=50)
        self.assertEqual([f.file_id for f in result["files"]], ["10", "11"])
        self.assertTrue(result["files"][0].is_dir)
        self.assertEqual(result["path"][-1], {"file_id": "10", "name": "dir"})
        self.assertEqual(result["count"], 2)

    async def test_empty_move_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = SequenceHTTPClient([])
            client = await self._make(tmp, http)
            self.assertEqual(await client.move_files([], "9"), 0)
        self.assertEqual(http.calls, [])


if __name__ == "__main__":
    unittest.main()
