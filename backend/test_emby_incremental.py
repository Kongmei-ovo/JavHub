from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from modules.emby_client import EmbyClient
from test_support.postgres import TempPostgresMixin


class EmbyIncrementalClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_items_with_people_passes_min_date_last_saved(self):
        client = EmbyClient("http://emby.test", "token")
        since_iso = "2026-06-01T12:34:56Z"

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {"Items": [], "TotalRecordCount": 0}

            await client.get_items_with_people(
                limit=25,
                start=50,
                min_date_last_saved=since_iso,
            )

        get_mock.assert_awaited_once_with(
            "/Items",
            params={
                "limit": 25,
                "startIndex": 50,
                "includeItemTypes": "Movie",
                "recursive": "true",
                "fields": "People,PremiereDate,ProductionYear",
                "MinDateLastSaved": since_iso,
            },
        )

    async def test_collect_incremental_movies_with_actors_uses_since_on_each_page(self):
        client = EmbyClient("http://emby.test", "token")
        since_iso = "2026-06-01T12:34:56Z"

        with patch.object(client, "get_items_with_people", new_callable=AsyncMock) as get_mock:
            get_mock.side_effect = [
                {
                    "items": [
                        {
                            "Id": "item-1",
                            "Name": "Updated Movie",
                            "FileName": "UPDATED-001.mp4",
                            "ProductionYear": 2026,
                            "People": [
                                {
                                    "Id": "901",
                                    "Name": "Actor One",
                                    "Type": "Actor",
                                    "PrimaryImageTag": "tag-901",
                                }
                            ],
                        }
                    ],
                    "totalCount": 1,
                }
            ]

            actors, total = await client.collect_incremental_movies_with_actors(since_iso=since_iso)

        self.assertEqual(total, 1)
        self.assertEqual(
            actors,
            [
                {
                    "actress_id": 901,
                    "actress_name": "Actor One",
                    "video_count": 1,
                    "items": [
                        {
                            "item_id": "item-1",
                            "title": "Updated Movie",
                            "filename": "UPDATED-001.mp4",
                            "production_year": 2026,
                        }
                    ],
                    "image_tag": "tag-901",
                }
            ],
        )
        get_mock.assert_awaited_once_with(
            limit=500,
            start=0,
            min_date_last_saved=since_iso,
        )


class SnapshotCloneTest(TempPostgresMixin, unittest.TestCase):
    def test_clone_snapshot_copies_videos_to_new_key_without_mutating_source_rows(self):
        from database import create_snapshot_key, get_snapshot_videos, save_emby_actors_snapshot, save_emvy_snapshot
        from database.snapshot import clone_snapshot

        source_key = create_snapshot_key()
        save_emby_actors_snapshot(
            source_key,
            [{"actress_id": 901, "actress_name": "Actor One", "video_count": 2}],
        )
        save_emvy_snapshot(source_key, 901, "Actor One", "item-1", "Old Title", "OLD-001.mp4")
        save_emvy_snapshot(source_key, 901, "Actor One", "item-2", "Keep Title", "KEEP-002.mp4")

        cloned_key = clone_snapshot(source_key)
        save_emvy_snapshot(cloned_key, 901, "Actor One", "item-3", "Delta Title", "DELTA-003.mp4")

        self.assertNotEqual(cloned_key, source_key)
        self.assertEqual(
            [video["title"] for video in get_snapshot_videos(source_key, 901)],
            ["Keep Title", "Old Title"],
        )
        self.assertEqual(
            [video["title"] for video in get_snapshot_videos(cloned_key, 901)],
            ["Delta Title", "Keep Title", "Old Title"],
        )


class IncrementalCollectJobTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_incremental_collect_clones_latest_snapshot_and_upserts_delta_only(self):
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
        save_emvy_snapshot(source_key, 901, "Actor One", "item-1", "Old Title", "OLD-001.mp4")
        save_emvy_snapshot(source_key, 901, "Actor One", "item-2", "Keep Title", "KEEP-002.mp4")

        job_id = add_inventory_job("collect")
        fake_emby = AsyncMock()
        fake_emby.collect_incremental_movies_with_actors.return_value = (
            [
                {
                    "actress_id": 901,
                    "actress_name": "Actor One",
                    "video_count": 1,
                    "items": [
                        {
                            "item_id": "item-1",
                            "title": "Updated Title",
                            "filename": "UPDATED-001.mp4",
                        }
                    ],
                }
            ],
            1,
        )

        with (
            patch("scheduler.inventory_tasks.get_emby_client", return_value=fake_emby),
            patch("config.Config.actor_mapping_auto_match_after_collect", new_callable=PropertyMock, return_value=False),
        ):
            await run_collect_job(job_id, mode="incremental")

        job = get_inventory_job(job_id)
        new_key = job["result"]["snapshot_key"]
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["mode"], "incremental")
        self.assertNotEqual(new_key, source_key)
        self.assertEqual(
            [(video["emby_item_id"], video["title"]) for video in get_snapshot_videos(source_key, 901)],
            [("item-2", "Keep Title"), ("item-1", "Old Title")],
        )
        self.assertEqual(
            [(video["emby_item_id"], video["title"]) for video in get_snapshot_videos(new_key, 901)],
            [("item-2", "Keep Title"), ("item-1", "Updated Title")],
        )
        fake_emby.collect_incremental_movies_with_actors.assert_awaited_once()
        since_iso = fake_emby.collect_incremental_movies_with_actors.await_args.kwargs["since_iso"]
        self.assertTrue(str(since_iso).strip())


class InventoryTriggerModeTest(unittest.TestCase):
    def test_trigger_collect_job_passes_requested_mode_to_background_runner(self):
        from routers.inventory import TriggerJobRequest, trigger_job

        req = TriggerJobRequest(job_type="collect", mode="incremental")

        with (
            patch("routers.inventory.add_inventory_job", return_value=42),
            patch("scheduler.inventory_tasks.run_inventory_job") as run_inventory_job,
        ):
            response = trigger_job(req)

        self.assertEqual(response, {"job_id": 42, "status": "pending"})
        run_inventory_job.assert_called_once_with(42, mode="incremental")


if __name__ == "__main__":
    unittest.main()
