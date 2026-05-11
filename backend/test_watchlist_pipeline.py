from __future__ import annotations

import os
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


class DownloadCandidateDatabaseTest(TempDbMixin, unittest.TestCase):
    def test_candidate_upsert_dedupes_by_content_and_source(self):
        from database import list_download_candidates, upsert_download_candidate

        first = upsert_download_candidate(
            content_id="SIVR-438",
            title="First",
            actress_id=1,
            source="subscription",
        )
        second = upsert_download_candidate(
            content_id="SIVR-438",
            title="Second",
            actress_id=1,
            source="subscription",
        )

        rows = list_download_candidates(source="subscription")
        self.assertEqual(len(rows), 1)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(rows[0]["title"], "Second")


class ActorMappingDatabaseTest(TempDbMixin, unittest.TestCase):
    def test_confirm_ignore_and_delete_mapping(self):
        from database import (
            confirm_actor_mapping,
            delete_actor_mapping,
            get_confirmed_actor_mapping,
            ignore_actor_mapping,
            list_actor_mappings,
        )

        mapping_id = confirm_actor_mapping("emby-1", "Emby Name", 123, "JavInfo Name")
        confirmed = get_confirmed_actor_mapping("emby-1")
        self.assertEqual(confirmed["javinfo_actress_id"], 123)
        self.assertEqual(confirmed["status"], "confirmed")

        ignore_actor_mapping("emby-2", "Ignored")
        ignore_actor_mapping("emby-2", "Ignored Again")
        ignored = list_actor_mappings(status="ignored")
        self.assertEqual(len(ignored), 1)
        self.assertEqual(ignored[0]["emby_actor_name"], "Ignored Again")

        self.assertTrue(delete_actor_mapping(mapping_id))
        self.assertIsNone(get_confirmed_actor_mapping("emby-1"))


class WatchlistPipelineTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_subscription_pipeline_creates_candidate_for_missing_movie(self):
        from services.watchlist_pipeline import WatchlistPipeline

        info_client = AsyncMock()
        info_client.get_actress_videos.return_value = {
            "data": [
                {
                    "content_id": "sivr438",
                    "dvd_id": "SIVR-438",
                    "title_ja": "Title",
                    "release_date": "2026-05-01",
                }
            ]
        }
        emby_client = AsyncMock()
        emby_client.check_exists.return_value = False

        pipeline = WatchlistPipeline(info_client=info_client, emby_client=emby_client)
        result = await pipeline.generate_candidates_for_actress(1, "Actor", "subscription")

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["new_movies_count"], 1)
        self.assertEqual(result["candidates"][0]["dvd_id"], "SIVR-438")
        info_client.get_actress_videos.assert_awaited_once()
        self.assertEqual(info_client.get_actress_videos.await_args.kwargs["include_supplement"], "1")


class DownloadCandidateRouterTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_approve_candidate_requires_magnet_and_creates_download_task(self):
        from database import update_download_candidate_magnet, upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(content_id="SIVR-438", title="Title")

        with self.assertRaises(Exception):
            await downloads.approve_candidate(candidate["id"])

        update_download_candidate_magnet(candidate["id"], "magnet:?xt=urn:btih:abc")
        with patch.object(downloads.downloader_service, "create_download_task", new_callable=AsyncMock) as create_task:
            create_task.return_value = 42
            result = await downloads.approve_candidate(candidate["id"])

        self.assertEqual(result["download_task_id"], 42)
        self.assertEqual(result["candidate"]["status"], "sent")

    async def test_list_candidates_filters_status(self):
        from database import upsert_download_candidate
        from routers import downloads

        upsert_download_candidate(content_id="SIVR-438", source="subscription", status="candidate")
        upsert_download_candidate(content_id="ABP-588", source="subscription", status="candidate", magnet="magnet:?x")
        upsert_download_candidate(content_id="MIAA-999", source="inventory", status="rejected")

        result = await downloads.list_candidates(status="candidate", needs_magnet=True)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["data"][0]["content_id"], "SIVR-438")


class ActorMappingRouterTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_confirm_ignore_and_list_mapping_api(self):
        from routers import inventory

        await inventory.confirm_mapping(inventory.ActorMappingRequest(
            emby_actor_id="emby-1",
            emby_actor_name="Emby Name",
            javinfo_actress_id=123,
            javinfo_actress_name="Jav Name",
        ))
        await inventory.ignore_mapping(inventory.ActorMappingRequest(
            emby_actor_id="emby-2",
            emby_actor_name="Ignored",
        ))

        confirmed = await inventory.list_mappings(status="confirmed")
        ignored = await inventory.list_mappings(status="ignored")

        self.assertEqual(len(confirmed["data"]), 1)
        self.assertEqual(confirmed["data"][0]["javinfo_actress_id"], 123)
        self.assertEqual(len(ignored["data"]), 1)


class InventoryMappingGuardTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_actor_compare_skips_unmapped_emby_actor(self):
        from database import (
            add_inventory_job,
            create_snapshot_key,
            save_emby_actors_snapshot,
            update_inventory_job,
            get_inventory_job,
        )
        from scheduler.inventory_tasks import run_actor_compare_job

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 900,
            "actress_name": "Emby Actor",
            "video_count": 1,
        }])
        job_id = add_inventory_job("actor", actor_id=900, snapshot_key=snapshot_key)

        await run_actor_compare_job(job_id, 900, snapshot_key)
        job = get_inventory_job(job_id)

        self.assertEqual(job["status"], "completed")
        self.assertIn("unmapped=1", job["error_msg"])

    async def test_actor_compare_for_confirmed_mapping_creates_inventory_candidate(self):
        from database import (
            add_inventory_job,
            confirm_actor_mapping,
            create_snapshot_key,
            list_download_candidates,
            save_emby_actors_snapshot,
            update_inventory_actor_stats,
            get_inventory_job,
        )
        from scheduler.inventory_tasks import run_actor_compare_job

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "Emby Actor",
            "video_count": 1,
        }])
        confirm_actor_mapping("901", "Emby Actor", 123, "Jav Actress")
        job_id = add_inventory_job("actor", actor_id=901, snapshot_key=snapshot_key)

        fake_pipeline = AsyncMock()
        fake_pipeline.fetch_actress_videos.return_value = [{
            "content_id": "sivr438",
            "dvd_id": "SIVR-438",
            "title_ja": "Mapped Missing",
            "release_date": "2026-05-01",
        }]
        with patch("scheduler.inventory_tasks.WatchlistPipeline", return_value=fake_pipeline):
            await run_actor_compare_job(job_id, 901, snapshot_key)

        candidates = list_download_candidates(source="inventory")
        job = get_inventory_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["dvd_id"], "SIVR-438")


class InventoryFillRouterTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fill_video_creates_candidate_instead_of_download_task(self):
        from database import add_missing_video, list_download_candidates, get_download_tasks
        from routers import inventory

        add_missing_video("SIVR-438", 1, "Missing", "2026-05-01", "")
        fake_info = AsyncMock()
        fake_info.get_video.return_value = {
            "content_id": "sivr438",
            "dvd_id": "SIVR-438",
            "title_ja": "Filled Candidate",
            "jacket_thumb_url": "cover.jpg",
        }
        with patch("routers.inventory.get_info_client", return_value=fake_info):
            result = await inventory.fill_video("SIVR-438")

        self.assertTrue(result["success"])
        self.assertEqual(len(list_download_candidates(source="inventory")), 1)
        self.assertEqual(get_download_tasks(), [])
