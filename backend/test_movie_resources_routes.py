from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

from test_support.client import create_router_test_client
from test_support.postgres import TempPostgresMixin


RESOURCE = {
    "id": 9,
    "movie_id": "dmm:abc123",
    "provider": "open115",
    "remote_file_id": "file-1",
    "parent_id": "folder-1",
    "pick_code": "pick-1",
    "name": "movie.mkv",
    "extension": "mkv",
    "size": 123,
    "duration": 456,
    "resource_type": "video",
    "status": "ready",
    "is_default": 1,
    "download_task_id": 7,
}


class MovieResourcesRoutesTests(unittest.TestCase):
    def _client(self):
        from routers.movie_resources import router

        return create_router_test_client(router)

    def test_list_resources_uses_stable_movie_id(self):
        with patch("routers.movie_resources.list_movie_resources", return_value=[RESOURCE]) as list_resources:
            response = self._client().get("/api/v1/movies/dmm%3Aabc123/resources")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["remote_file_id"], "file-1")
        list_resources.assert_called_once_with("dmm:abc123")

    def test_set_default_returns_404_when_resource_is_not_selectable(self):
        with patch("routers.movie_resources.set_default_movie_resource", return_value=False):
            response = self._client().post("/api/v1/movies/movie-1/resources/99/default")

        self.assertEqual(response.status_code, 404)

    def test_delete_only_removes_reference_for_matching_movie(self):
        deleted = {
            "provider": "local",
            "remote_file_id": "",
            "pick_code": "",
            "is_default": 0,
        }
        with patch("routers.movie_resources.delete_movie_resource", return_value=deleted) as delete_resource:
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        delete_resource.assert_called_once_with("movie-1", 9)

    def test_delete_resource_also_removes_from_115(self):
        deleted = {
            "provider": "open115",
            "remote_file_id": "file-1",
            "parent_id": "folder-1",
            "pick_code": "pick-1",
            "is_default": 1,
        }
        delete_files = AsyncMock()
        with patch("routers.movie_resources.delete_movie_resource", return_value=deleted) as delete_resource, patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": True}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        delete_resource.assert_called_once_with("movie-1", 9)
        delete_files.assert_awaited_once_with(["file-1"], parent_id="folder-1")

    def test_delete_resource_skips_115_when_disabled(self):
        deleted = {
            "provider": "open115",
            "remote_file_id": "file-1",
            "parent_id": "folder-1",
            "pick_code": "pick-1",
            "is_default": 1,
        }
        delete_files = AsyncMock()
        with patch("routers.movie_resources.delete_movie_resource", return_value=deleted), patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": "false"}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        delete_files.assert_not_awaited()

    def test_delete_resource_skips_115_for_other_providers(self):
        deleted = {
            "provider": "local",
            "remote_file_id": "file-1",
            "pick_code": "pick-1",
            "is_default": 1,
        }
        delete_files = AsyncMock()
        with patch("routers.movie_resources.delete_movie_resource", return_value=deleted), patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": True}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        delete_files.assert_not_awaited()

    def test_delete_resource_keeps_200_when_115_delete_fails(self):
        deleted = {
            "provider": "open115",
            "remote_file_id": "file-1",
            "parent_id": "folder-1",
            "pick_code": "pick-1",
            "is_default": 1,
        }
        delete_files = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("routers.movie_resources.delete_movie_resource", return_value=deleted) as delete_resource, patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": True}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        delete_resource.assert_called_once_with("movie-1", 9)
        delete_files.assert_awaited_once_with(["file-1"], parent_id="folder-1")

    def test_open115_delete_files_ignores_empty_inputs(self):
        from services.open115 import Open115Client

        client = Open115Client(config_obj=SimpleNamespace(_config={}), http_client=AsyncMock())
        auth_request = AsyncMock()
        with patch.object(client, "_auth_request", auth_request):
            asyncio.run(client.delete_files(["", "  ", None]))

        auth_request.assert_not_awaited()

    def test_open115_delete_files_posts_normalized_ids_without_parent_id(self):
        from services.open115 import Open115Client

        client = Open115Client(config_obj=SimpleNamespace(_config={}), http_client=AsyncMock())
        auth_request = AsyncMock()
        with patch.object(client, "_auth_request", auth_request):
            asyncio.run(client.delete_files(["a", " b ", ""], parent_id=None))
            asyncio.run(client.delete_files(["a", " b ", ""], parent_id="  "))

        self.assertEqual(
            auth_request.await_args_list,
            [
                call(
                    "POST",
                    "/open/ufile/delete",
                    data={"file_ids": "a,b"},
                ),
                call(
                    "POST",
                    "/open/ufile/delete",
                    data={"file_ids": "a,b"},
                ),
            ],
        )

    def test_open115_delete_files_posts_normalized_parent_id(self):
        from services.open115 import Open115Client

        client = Open115Client(config_obj=SimpleNamespace(_config={}), http_client=AsyncMock())
        auth_request = AsyncMock()
        with patch.object(client, "_auth_request", auth_request):
            asyncio.run(client.delete_files(["a", " b ", ""], parent_id=" folder-1 "))

        auth_request.assert_awaited_once_with(
            "POST",
            "/open/ufile/delete",
            data={"file_ids": "a,b", "parent_id": "folder-1"},
        )


class MovieResourcesRoutesDatabaseTests(TempPostgresMixin, unittest.TestCase):
    def _client(self):
        from routers.movie_resources import router

        return create_router_test_client(router)

    def test_delete_resource_passes_real_database_parent_id_to_115(self):
        from database import get_movie_resource, upsert_movie_resource

        resource_id, _ = upsert_movie_resource(
            movie_id="REAL-1",
            provider="open115",
            remote_file_id="file-real",
            parent_id="folder-real",
            name="REAL-1.mp4",
            resource_type="video",
            status="ready",
            is_default=True,
        )
        delete_files = AsyncMock()
        with patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": True}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete(f"/api/v1/movies/REAL-1/resources/{resource_id}")

        self.assertEqual(response.status_code, 200)
        delete_files.assert_awaited_once_with(["file-real"], parent_id="folder-real")
        self.assertIsNone(get_movie_resource(resource_id))

    def test_delete_resource_passes_empty_real_database_parent_id_to_115(self):
        from database import get_movie_resource, upsert_movie_resource

        resource_id, _ = upsert_movie_resource(
            movie_id="REAL-2",
            provider="open115",
            remote_file_id="file-no-parent",
            name="REAL-2.mp4",
            resource_type="video",
            status="ready",
            is_default=True,
        )
        delete_files = AsyncMock()
        with patch(
            "routers.movie_resources.config._config",
            {"open115": {"delete_on_remove": True}},
        ), patch("services.open115.open115_client.delete_files", new=delete_files):
            response = self._client().delete(f"/api/v1/movies/REAL-2/resources/{resource_id}")

        self.assertEqual(response.status_code, 200)
        delete_files.assert_awaited_once_with(["file-no-parent"], parent_id="")
        self.assertIsNone(get_movie_resource(resource_id))


if __name__ == "__main__":
    unittest.main()
