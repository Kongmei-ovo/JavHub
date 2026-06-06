from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class InventoryProvenanceDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_missing_video_columns_and_candidate_inventory_provenance_round_trip(self):
        from database import add_missing_video, get_missing_video, list_download_candidates, upsert_candidate_from_video

        add_missing_video("MISS-001", 901, "Missing", "2026-05-01", "missing.jpg")
        candidate = upsert_candidate_from_video(
            video={
                "content_id": "MISS-001",
                "dvd_id": "MISS-001",
                "title_ja": "Missing",
                "release_date": "2026-05-01",
            },
            actress_id=123,
            actress_name="Jav Actor",
            source="inventory",
            reason="inventory_compare:snap-1",
            provenance={
                "snapshot_key": "snap-1",
                "matched_emby_item_id": None,
                "matched_filename": None,
            },
        )

        missing = get_missing_video("MISS-001")
        rows = list_download_candidates(source="inventory")

        self.assertIn("matched_emby_item_id", missing)
        self.assertIn("matched_filename", missing)
        self.assertIsNone(missing["matched_emby_item_id"])
        self.assertIsNone(missing["matched_filename"])
        self.assertEqual(candidate["inventory_provenance"]["snapshot_key"], "snap-1")
        self.assertEqual(rows[0]["inventory_provenance"]["matched_emby_item_id"], None)

    def test_owned_inventory_video_exposes_matched_aliases(self):
        from database import get_inventory_videos, upsert_inventory_video

        upsert_inventory_video("SIVR-438", "emby-hit", 901, "Owned", "2026-04-01", "owned.jpg", matched_filename="/media/SIVR-438.mp4")

        videos = get_inventory_videos(901)

        self.assertEqual(videos[0]["matched_emby_item_id"], "emby-hit")
        self.assertEqual(videos[0]["matched_filename"], "/media/SIVR-438.mp4")


class InventoryProvenanceCompareTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_compare_records_owned_match_projection_and_missing_candidate_provenance(self):
        from database import (
            add_inventory_job,
            confirm_actor_mapping,
            create_snapshot_key,
            get_inventory_videos,
            list_download_candidates,
            save_emby_actors_snapshot,
            save_emvy_snapshot,
            upsert_inventory_actor,
        )
        from scheduler.inventory_tasks import run_compare_job

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{"actress_id": 901, "actress_name": "Emby Actor", "video_count": 1}])
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "emby-hit", "Owned Title", "/media/SIVR-438.mp4")
        upsert_inventory_actor(901, "Emby Actor")
        confirm_actor_mapping("901", "Emby Actor", 123, "Jav Actor")
        job_id = add_inventory_job("full", snapshot_key=snapshot_key)

        fake_pipeline = AsyncMock()
        fake_pipeline.fetch_actress_videos.return_value = [
            {
                "content_id": "SIVR-438",
                "dvd_id": "SIVR-438",
                "title_ja": "Owned Jav Title",
                "release_date": "2026-04-01",
                "jacket_thumb_url": "owned.jpg",
            },
            {
                "content_id": "MISS-001",
                "dvd_id": "MISS-001",
                "title_ja": "Missing Jav Title",
                "release_date": "2026-05-01",
                "jacket_thumb_url": "missing.jpg",
            },
        ]

        with patch("scheduler.inventory_tasks.WatchlistPipeline", return_value=fake_pipeline):
            await run_compare_job(job_id, snapshot_key)

        owned = get_inventory_videos(901)
        candidates = list_download_candidates(source="inventory")

        self.assertEqual(len(owned), 1)
        self.assertEqual(owned[0]["content_id"], "SIVR-438")
        self.assertEqual(owned[0]["matched_emby_item_id"], "emby-hit")
        self.assertEqual(owned[0]["matched_filename"], "/media/SIVR-438.mp4")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["content_id"], "MISS-001")
        self.assertEqual(candidates[0]["inventory_provenance"]["snapshot_key"], snapshot_key)
        self.assertIsNone(candidates[0]["inventory_provenance"]["matched_emby_item_id"])
