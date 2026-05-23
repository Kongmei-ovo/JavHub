from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from routers import authors
from test_support.cache import FakeRedisMixin


class AuthorsRouterTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):

    async def test_list_authors_caches_by_query_params(self):
        mock_client = AsyncMock()
        mock_client.list_authors.side_effect = [
            {"data": [{"id": 1, "name": "author-one"}], "page": 1, "page_size": 20},
            {"data": [{"id": 2, "name": "author-two"}], "page": 2, "page_size": 20},
            {"data": [{"id": 3, "name": "searched"}], "page": 1, "page_size": 20},
        ]

        with patch("routers.authors.get_info_client", return_value=mock_client):
            first = await authors.list_authors(q=None, page=1, page_size=20)
            first_cached = await authors.list_authors(q=None, page=1, page_size=20)
            second_page = await authors.list_authors(q=None, page=2, page_size=20)
            searched = await authors.list_authors(q="searched", page=1, page_size=20)

        self.assertEqual(first_cached, first)
        self.assertEqual(second_page["data"], [{"id": 2, "name": "author-two"}])
        self.assertEqual(searched["data"], [{"id": 3, "name": "searched"}])
        self.assertEqual(mock_client.list_authors.await_count, 3)
        mock_client.list_authors.assert_any_await(q=None, page=1, page_size=20)
        mock_client.list_authors.assert_any_await(q=None, page=2, page_size=20)
        mock_client.list_authors.assert_any_await(q="searched", page=1, page_size=20)


if __name__ == "__main__":
    unittest.main()
