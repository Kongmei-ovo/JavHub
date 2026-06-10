"""Incremental collect must drop rows for items deleted on the Emby side.

Without this reconciliation, an Emby-side delete leaves a stale row in the
snapshot forever, so the compare stage keeps reporting "owned" and never
re-downloads. This test pins the new behavior.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from test_support.postgres import TempPostgresMixin


class IncrementalDeleteSyncTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_incremental_collect_prunes_items_no_longer_in_emby(self):
        from database import (
            add_inventory_job,
            create_snapshot_key,
            get_inventory_job,
            get_snapshot_videos,
            save_emby_actors_snapshot,
            save_emvy_snapshot,
        )
        from scheduler.inventory_tasks import run_collect_job

        source_key = create_snapshot_key()
        save_emby_actors_snapshot(
            source_key,
            [{"actress_id": 901, "actress_name": "Actor One", "video_count": 2}],
        )
        save_emvy_snapshot(source_key, 901, "Actor One", "item-keep", "Keep", "K.mp4")
        save_emvy_snapshot(source_key, 901, "Actor One", "item-gone", "Gone", "G.mp4")

        job_id = add_inventory_job("collect")
        fake_emby = AsyncMock()
        fake_emby.collect_incremental_movies_with_actors.return_value = ([], 0)
        # Emby now reports only ``item-keep``; ``item-gone`` was deleted upstream.
        fake_emby.iter_item_ids.return_value = ["item-keep"]

        with (
            patch("scheduler.inventory_tasks.get_emby_client", return_value=fake_emby),
            patch("config.Config.actor_mapping_auto_match_after_collect", new_callable=PropertyMock, return_value=False),
        ):
            await run_collect_job(job_id, mode="incremental")

        job = get_inventory_job(job_id)
        new_key = job["result"]["snapshot_key"]
        self.assertEqual(job["status"], "completed")
        # Old snapshot is untouched (audit trail).
        self.assertEqual(
            [video["emby_item_id"] for video in get_snapshot_videos(source_key, 901)],
            ["item-gone", "item-keep"],
        )
        # New snapshot has the deleted row pruned.
        self.assertEqual(
            [video["emby_item_id"] for video in get_snapshot_videos(new_key, 901)],
            ["item-keep"],
        )
        self.assertGreaterEqual(job["result"].get("deleted_from_snapshot", 0), 1)

    async def test_incremental_collect_does_not_prune_when_emby_returns_empty(self):
        """Don't wipe the snapshot just because Emby briefly returned no items."""
        from database import (
            add_inventory_job,
            create_snapshot_key,
            get_inventory_job,
            get_snapshot_videos,
            save_emby_actors_snapshot,
            save_emvy_snapshot,
        )
        from scheduler.inventory_tasks import run_collect_job

        source_key = create_snapshot_key()
        save_emby_actors_snapshot(
            source_key,
            [{"actress_id": 901, "actress_name": "Actor One", "video_count": 1}],
        )
        save_emvy_snapshot(source_key, 901, "Actor One", "item-keep", "Keep", "K.mp4")

        job_id = add_inventory_job("collect")
        fake_emby = AsyncMock()
        fake_emby.collect_incremental_movies_with_actors.return_value = ([], 0)
        fake_emby.iter_item_ids.return_value = []  # Emby hiccup — must NOT wipe

        with (
            patch("scheduler.inventory_tasks.get_emby_client", return_value=fake_emby),
            patch("config.Config.actor_mapping_auto_match_after_collect", new_callable=PropertyMock, return_value=False),
        ):
            await run_collect_job(job_id, mode="incremental")

        job = get_inventory_job(job_id)
        new_key = job["result"]["snapshot_key"]
        self.assertEqual(job["status"], "completed")
        self.assertEqual(
            [video["emby_item_id"] for video in get_snapshot_videos(new_key, 901)],
            ["item-keep"],
        )
        self.assertEqual(job["result"].get("deleted_from_snapshot"), 0)


class SnapshotRetentionTest(TempPostgresMixin, unittest.TestCase):
    def test_prune_old_snapshots_keeps_recent_n(self):
        from database import save_emby_actors_snapshot
        from database.snapshot import (
            clone_snapshot,
            create_snapshot_key,
            list_snapshot_keys,
            prune_old_snapshots,
        )

        keys = []
        for idx in range(6):
            key = create_snapshot_key()
            save_emby_actors_snapshot(
                key,
                [{"actress_id": 100 + idx, "actress_name": f"A{idx}", "video_count": 1}],
            )
            keys.append(key)

        before = list_snapshot_keys()
        self.assertEqual(len(before), 6)

        dropped = prune_old_snapshots(keep=3)

        remaining = list_snapshot_keys()
        self.assertEqual(len(remaining), 3)
        # Newer keys survive; older ones got pruned.
        self.assertEqual(set(remaining) & set(dropped), set())
        self.assertEqual(len(dropped), 3)


if __name__ == "__main__":
    unittest.main()
