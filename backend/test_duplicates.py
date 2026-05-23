from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch


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


class DuplicateRouteTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
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

