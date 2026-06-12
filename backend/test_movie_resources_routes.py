from __future__ import annotations

import unittest
from unittest.mock import patch

from test_support.client import create_router_test_client


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
        with patch("routers.movie_resources.delete_movie_resource", return_value=True) as delete_resource:
            response = self._client().delete("/api/v1/movies/movie-1/resources/9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        delete_resource.assert_called_once_with("movie-1", 9)


if __name__ == "__main__":
    unittest.main()
