from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from modules.emby_client import EmbyClient


class EmbyCheckExistsCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_check_exists_reuses_lookup_cache_for_same_normalized_code(self):
        client = EmbyClient("http://emby.test", "token")

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {
                "Items": [
                    {
                        "Id": "emby-1",
                        "Name": "ABC-123 Title",
                        "FileName": "/media/ABC-123.mp4",
                    }
                ]
            }

            self.assertTrue(await client.check_exists("abc-123"))
            self.assertTrue(await client.check_exists("ABC-123"))

        get_mock.assert_awaited_once_with(
            "/Items",
            params={
                "limit": 10,
                "includeItemTypes": "Movie",
                "recursive": "true",
                "searchTerm": "ABC-123",
            },
        )

    async def test_lookup_returns_first_matching_emby_item_provenance(self):
        client = EmbyClient("http://emby.test", "token")

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {
                "Items": [
                    {
                        "Id": "noise",
                        "Name": "ABC-1234 Similar but not same",
                        "FileName": "/media/ABC-1234.mp4",
                    },
                    {
                        "Id": "emby-123",
                        "Name": "ABC-123 Correct Title",
                        "FileName": "/media/ABC-123.mp4",
                    },
                ]
            }

            result = await client.lookup("abc-123")

        self.assertEqual(
            result,
            {"exists": True, "emby_item_id": "emby-123", "name": "ABC-123 Correct Title"},
        )

    async def test_lookup_refreshes_after_ttl_expires(self):
        client = EmbyClient("http://emby.test", "token")

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {"Items": [{"Id": "emby-1", "Name": "ABC-123 Title"}]}

            self.assertIsNotNone(await client.lookup("ABC-123"))
            cached_at, cached_result = client._exists_cache["ABC-123"]
            client._exists_cache["ABC-123"] = (cached_at - 30.1, cached_result)
            self.assertIsNotNone(await client.lookup("ABC-123"))

        self.assertEqual(get_mock.await_count, 2)

    async def test_clear_exists_cache_forces_next_lookup_to_query_emby(self):
        client = EmbyClient("http://emby.test", "token")

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {"Items": [{"Id": "emby-1", "Name": "ABC-123 Title"}]}

            await client.lookup("ABC-123")
            client.clear_exists_cache()
            await client.lookup("ABC-123")

        self.assertEqual(get_mock.await_count, 2)


if __name__ == "__main__":
    unittest.main()
