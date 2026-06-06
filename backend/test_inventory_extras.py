from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.cache import FakeRedisMixin
from test_support.client import create_router_test_client


class InventoryExtrasServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_extras_flags_uncoded_and_unknown_snapshot_videos(self):
        from services import inventory_extras

        info_client = AsyncMock()
        info_client.get_all_actress_videos.return_value = {
            "data": [
                {"dvd_id": "ABP-123"},
                {"content_id": "MIAA-777"},
            ]
        }
        info_client.batch_lookup_by_dvd_id.return_value = {
            "ABP-123": {"dvd_id": "ABP-123"},
        }
        rows = [
            {
                "emby_item_id": "emby-1",
                "title": "ABP-123 local title",
                "filename": "/media/ABP-123.mp4",
            },
            {
                "emby_item_id": "emby-2",
                "title": "Local only",
                "filename": "/media/ZZZ-999.mp4",
            },
            {
                "emby_item_id": "emby-3",
                "title": "bad title",
                "filename": "/media/no-code-file.mp4",
            },
            {
                "emby_item_id": "emby-4",
                "title": "javinfo known",
                "filename": "/media/MIAA-777.mp4",
            },
        ]

        with patch.object(inventory_extras, "iter_snapshot_videos_by_actor", Mock(return_value=rows)) as videos:
            result = await inventory_extras.list_extras(
                "snap-1",
                actor_id=123,
                limit=10,
                info_client=info_client,
            )

        videos.assert_called_once_with("snap-1", 123, 10)
        info_client.get_all_actress_videos.assert_awaited_once_with(123, include_supplement="1", cache_bypass=True)
        info_client.batch_lookup_by_dvd_id.assert_awaited_once_with(["ZZZ-999"])
        self.assertEqual(
            [
                (item["emby_item_id"], item["filename"], item["reason"])
                for item in result
            ],
            [
                ("emby-2", "/media/ZZZ-999.mp4", "not_in_javinfo"),
                ("emby-3", "/media/no-code-file.mp4", "no_code"),
            ],
        )

    async def test_list_extras_uses_batch_lookup_without_actor_filmography(self):
        from services import inventory_extras

        info_client = AsyncMock()
        info_client.batch_lookup_by_dvd_id.return_value = {}
        rows = [
            {
                "emby_item_id": "emby-1",
                "title": "PRED-456",
                "filename": "PRED-456.mp4",
            },
        ]

        with patch.object(inventory_extras, "iter_snapshot_videos_by_actor", Mock(return_value=rows)):
            result = await inventory_extras.list_extras("snap-1", actor_id=None, limit=50, info_client=info_client)

        info_client.get_all_actress_videos.assert_not_called()
        info_client.batch_lookup_by_dvd_id.assert_awaited_once_with(["PRED-456"])
        self.assertEqual(result[0]["reason"], "not_in_javinfo")

    async def test_list_extras_deduplicates_same_emby_item_across_snapshot_actor_rows(self):
        from services import inventory_extras

        info_client = AsyncMock()
        info_client.batch_lookup_by_dvd_id.return_value = {}
        rows = [
            {
                "emby_item_id": "emby-1",
                "title": "no code title",
                "filename": "uncoded.mp4",
            },
            {
                "emby_item_id": "emby-1",
                "title": "no code title",
                "filename": "uncoded.mp4",
            },
        ]

        with patch.object(inventory_extras, "iter_snapshot_videos_by_actor", Mock(return_value=rows)):
            result = await inventory_extras.list_extras("snap-1", info_client=info_client)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["emby_item_id"], "emby-1")

    async def test_global_list_extras_overfetches_before_deduping_to_fill_unique_limit(self):
        from services import inventory_extras

        info_client = AsyncMock()
        info_client.batch_lookup_by_dvd_id.return_value = {}
        rows = [
            {"emby_item_id": "emby-1", "title": "uncoded one", "filename": ""},
            {"emby_item_id": "emby-1", "title": "uncoded one", "filename": ""},
            {"emby_item_id": "emby-2", "title": "uncoded two", "filename": ""},
        ]

        def fake_iter(_snapshot_key, _actor_id, limit):
            return rows[:limit]

        with patch.object(inventory_extras, "iter_snapshot_videos_by_actor", Mock(side_effect=fake_iter)):
            result = await inventory_extras.list_extras("snap-1", actor_id=None, limit=2, info_client=info_client)

        self.assertEqual([item["emby_item_id"] for item in result], ["emby-1", "emby-2"])


class InventoryExtrasDatabaseTest(unittest.TestCase):
    def test_iter_snapshot_videos_by_actor_filters_snapshot_actor_and_limit(self):
        from database import snapshot

        class Cursor:
            def __init__(self):
                self.calls = []

            def execute(self, sql, params):
                self.calls.append((sql, params))

            def fetchall(self):
                return [
                    {
                        "snapshot_key": "snap-1",
                        "actress_id": 10,
                        "emby_item_id": "emby-1",
                        "title": "A",
                        "filename": "A.mp4",
                    }
                ]

        class Conn:
            def __init__(self):
                self.cursor_obj = Cursor()

            def cursor(self):
                return self.cursor_obj

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        conn = Conn()
        with patch.object(snapshot, "get_db", Mock(return_value=conn)):
            rows = snapshot.iter_snapshot_videos_by_actor("snap-1", actor_id=10, limit=25)

        sql, params = conn.cursor_obj.calls[0]
        self.assertIn("snapshot_key = ?", sql)
        self.assertIn("actress_id = ?", sql)
        self.assertEqual(params, ["snap-1", 10, 25])
        self.assertEqual(rows[0]["emby_item_id"], "emby-1")


class InventoryExtrasRouteTest(FakeRedisMixin, unittest.TestCase):
    def test_extras_route_uses_latest_snapshot_and_30_second_cache(self):
        from routers import inventory

        captured = {}

        async def capture_cache(namespace, params, producer, ttl, bypass=False):
            captured.update({"namespace": namespace, "params": params, "ttl": ttl, "bypass": bypass})
            return await producer()

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")) as latest, \
            patch.object(inventory.inventory_extras, "list_extras", AsyncMock(return_value=[
                {"emby_item_id": "emby-1", "filename": "NO-CODE.mp4", "reason": "no_code"},
            ])) as list_extras, \
            patch.object(inventory, "get_or_set_response", capture_cache):
            response = create_router_test_client(inventory.router).get(
                "/api/v1/inventory/extras?actor_id=123&limit=10"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        latest.assert_called_once()
        list_extras.assert_awaited_once_with("snap-1", actor_id=123, limit=10)
        self.assertEqual(captured["namespace"], "inventory_extras")
        self.assertEqual(captured["params"], {"snapshot_key": "snap-1", "actor_id": 123, "limit": 10})
        self.assertEqual(captured["ttl"], 30)
        self.assertFalse(captured["bypass"])

    def test_extras_route_supports_cache_bypass(self):
        from routers import inventory

        captured = {}

        async def capture_cache(namespace, params, producer, ttl, bypass=False):
            captured["bypass"] = bypass
            return await producer()

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(inventory.inventory_extras, "list_extras", AsyncMock(return_value=[])), \
            patch.object(inventory, "get_or_set_response", capture_cache):
            response = create_router_test_client(inventory.router).get("/api/v1/inventory/extras?cache=0")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": [], "total": 0})
        self.assertTrue(captured["bypass"])


if __name__ == "__main__":
    unittest.main()
