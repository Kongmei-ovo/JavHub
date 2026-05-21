from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from routers import actors
from services import cache


class ActorsRouterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

    async def test_list_actors_caches_by_query_params(self):
        mock_client = AsyncMock()
        mock_client.list_actors.side_effect = [
            {"data": [{"id": 1, "name": "actor-one"}], "page": 1, "page_size": 20},
            {"data": [{"id": 2, "name": "actor-two"}], "page": 2, "page_size": 20},
            {"data": [{"id": 3, "name": "searched"}], "page": 1, "page_size": 20},
        ]

        with patch("routers.actors.get_info_client", return_value=mock_client):
            first = await actors.list_actors(q=None, page=1, page_size=20)
            first_cached = await actors.list_actors(q=None, page=1, page_size=20)
            second_page = await actors.list_actors(q=None, page=2, page_size=20)
            searched = await actors.list_actors(q="searched", page=1, page_size=20)

        self.assertEqual(first_cached, first)
        self.assertEqual(second_page["data"], [{"id": 2, "name": "actor-two"}])
        self.assertEqual(searched["data"], [{"id": 3, "name": "searched"}])
        self.assertEqual(mock_client.list_actors.await_count, 3)
        mock_client.list_actors.assert_any_await(q=None, page=1, page_size=20)
        mock_client.list_actors.assert_any_await(q=None, page=2, page_size=20)
        mock_client.list_actors.assert_any_await(q="searched", page=1, page_size=20)


if __name__ == "__main__":
    unittest.main()
