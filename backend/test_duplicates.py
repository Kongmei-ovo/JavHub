import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.postgres import TempPostgresMixin


class DuplicateRouteTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_duplicates_without_snapshot_does_not_run_live_scan_by_default(self):
        from routers import duplicates

        emby_client = AsyncMock()

        with patch.object(duplicates, "get_emby_client", return_value=emby_client):
            result = await duplicates.list_duplicates()

        emby_client.find_duplicates.assert_not_awaited()
        self.assertEqual(result["data"], [])
        self.assertEqual(result["total"], 0)
        self.assertIsNone(result["snapshot_key"])
        self.assertTrue(result["live_scan_available"])

    async def test_duplicates_are_built_from_latest_emby_snapshot(self):
        from database import create_snapshot_key, save_emby_actors_snapshot, save_emvy_snapshot
        from routers import duplicates

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "Emby Actor",
            "video_count": 2,
        }])
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-1", "ABP-123 Title", "")
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-2", "ABP-123 Title (1)", "")
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-3", "MIAA-777 Other", "")

        emby_client = AsyncMock()

        with patch.object(duplicates, "get_emby_client", return_value=emby_client):
            result = await duplicates.list_duplicates()

        emby_client.find_duplicates.assert_not_awaited()
        self.assertEqual(result["total"], 1)
        duplicate = result["data"][0]
        self.assertEqual(duplicate["content_id"], "ABP-123")
        self.assertEqual(duplicate["duplicate_count"], 2)
        self.assertEqual([item["emby_item_id"] for item in duplicate["items"]], ["item-1", "item-2"])

    async def test_snapshot_duplicate_candidates_filter_ignored_items_in_sql(self):
        from database import (
            add_ignored_duplicate,
            create_snapshot_key,
            get_snapshot_duplicate_candidates,
            save_emby_actors_snapshot,
            save_emvy_snapshot,
        )

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "Emby Actor",
            "video_count": 2,
        }])
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-1", "ABP-123 Title", "")
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-2", "ABP-123 Title (1)", "")
        add_ignored_duplicate("ABP-123", "item-2", "test")

        rows = get_snapshot_duplicate_candidates(snapshot_key)

        self.assertEqual([row["emby_item_id"] for row in rows], ["item-1"])

    def test_snapshot_duplicate_scan_uses_filtered_candidates_without_per_row_ignore_lookup(self):
        from routers import duplicates

        with patch.object(duplicates, "get_snapshot_duplicate_candidates", Mock(return_value=[
            {"emby_item_id": "item-1", "title": "ABP-123 Title", "filename": ""},
            {"emby_item_id": "item-2", "title": "ABP-123 Title (1)", "filename": ""},
        ])), \
            patch.object(duplicates, "is_duplicate_ignored", Mock(side_effect=AssertionError("per-row ignored lookup"))):
            result = duplicates._snapshot_duplicates_for_key("snap-1")

        self.assertEqual(result[0]["content_id"], "ABP-123")
        self.assertEqual(result[0]["duplicate_count"], 2)

    async def test_snapshot_duplicates_use_short_response_cache_with_bypass(self):
        from routers import duplicates

        with patch.object(duplicates, "_snapshot_duplicates_payload", side_effect=[
            ("snap-1", [{"content_id": "ABP-123"}]),
            ("snap-1", [{"content_id": "MIAA-777"}]),
            ("snap-1", [{"content_id": "JUQ-001"}]),
        ]) as snapshot_payload:
            first = await duplicates.list_duplicates()
            second = await duplicates.list_duplicates()
            bypassed = await duplicates.list_duplicates(cache_control="0")

        self.assertEqual(snapshot_payload.call_count, 2)
        self.assertEqual(first["data"][0]["content_id"], "ABP-123")
        self.assertEqual(second["data"][0]["content_id"], "ABP-123")
        self.assertEqual(bypassed["data"][0]["content_id"], "MIAA-777")
