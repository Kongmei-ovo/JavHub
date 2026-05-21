from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, PropertyMock, patch


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


class CandidateProcessorTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_manual_policy_does_not_send_download(self):
        from database import list_download_candidate_events, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock()) as create:
            result = await process_candidate(candidate["id"], policy="manual")

        self.assertEqual(result["action"], "manual_required")
        create.assert_not_awaited()
        events = list_download_candidate_events(candidate["id"])
        self.assertEqual(events[0]["action"], "policy_skipped")

    async def test_rules_policy_sends_candidate_with_magnet(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=7)):
            with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 7, "status": "downloading"}]):
                result = await process_candidate(candidate["id"], policy="rules")

        self.assertEqual(result["action"], "sent")
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "sent")

    async def test_auto_policy_enriches_missing_magnet_before_send(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            title="Title",
            source="inventory",
        )
        magnet = {
            "magnet": "magnet:?xt=urn:btih:456",
            "title": "SIVR-438 字幕 1080p",
            "size": "4.2GB",
            "hd": True,
            "subtitle": True,
            "resolution": "1080p",
            "quality": "HD",
        }

        with patch("services.candidate_processor.find_best_magnet", new=AsyncMock(return_value=magnet)):
            with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=9)):
                with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 9, "status": "downloading"}]):
                    result = await process_candidate(candidate["id"], policy="auto")

        updated = get_download_candidate(candidate["id"])
        self.assertEqual(result["action"], "sent")
        self.assertEqual(updated["status"], "sent")
        self.assertEqual(updated["magnet"], magnet["magnet"])

    async def test_find_best_magnet_accepts_http_torrent_result(self):
        from services.candidate_processor import find_best_magnet

        http_result = {
            "magnet": "",
            "download_url": "https://indexer.test/download/SIVR-438.torrent",
            "torrent_url": "https://indexer.test/download/SIVR-438.torrent",
            "title": "SIVR-438 1080p",
            "size": "2.0GB",
            "hd": True,
            "resolution": "1080p",
        }

        with patch("services.candidate_processor.register_all_sources"):
            with patch("services.candidate_processor.SourceRegistry.search_all", new=AsyncMock(return_value=[http_result])):
                result = await find_best_magnet({"content_id": "SIVR-438"})

        self.assertEqual(result["download_url"], "https://indexer.test/download/SIVR-438.torrent")
        self.assertEqual(result["torrent_url"], "https://indexer.test/download/SIVR-438.torrent")

    async def test_auto_policy_enriches_http_torrent_url_before_send(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            title="Title",
            source="inventory",
        )
        source_result = {
            "magnet": "",
            "download_url": "https://indexer.test/download/SIVR-438.torrent",
            "torrent_url": "https://indexer.test/download/SIVR-438.torrent",
            "title": "SIVR-438 1080p",
            "size": "2.0GB",
        }

        with patch("services.candidate_processor.find_best_magnet", new=AsyncMock(return_value=source_result)):
            with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=9)) as create:
                with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 9, "status": "downloading"}]):
                    result = await process_candidate(candidate["id"], policy="auto")

        updated = get_download_candidate(candidate["id"])
        self.assertEqual(result["action"], "sent")
        self.assertEqual(updated["status"], "sent")
        self.assertEqual(updated["magnet"], "https://indexer.test/download/SIVR-438.torrent")
        create.assert_awaited_once()
        self.assertEqual(create.await_args.kwargs["magnet"], "https://indexer.test/download/SIVR-438.torrent")

    async def test_rejected_and_sent_are_not_processed(self):
        from database import set_download_candidate_status, upsert_download_candidate
        from services.candidate_processor import process_candidate

        rejected = upsert_download_candidate(content_id="SIVR-438", source="inventory", magnet="magnet:a")
        sent = upsert_download_candidate(content_id="ABP-588", source="inventory", magnet="magnet:b")
        set_download_candidate_status(rejected["id"], "rejected")
        set_download_candidate_status(sent["id"], "sent", download_task_id=1)

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock()) as create:
            first = await process_candidate(rejected["id"], policy="auto")
            second = await process_candidate(sent["id"], policy="auto")

        self.assertEqual(first["action"], "skipped_status")
        self.assertEqual(second["action"], "skipped_status")
        create.assert_not_awaited()

    async def test_downloader_failure_marks_candidate_failed_and_records_event(self):
        from database import get_download_candidate, list_download_candidate_events, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=12)):
            with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 12, "status": "failed", "error_msg": "OpenList API 调用失败"}]):
                result = await process_candidate(candidate["id"], policy="rules")

        self.assertEqual(result["action"], "failed_downloader")
        updated = get_download_candidate(candidate["id"])
        self.assertEqual(updated["status"], "failed")
        self.assertEqual(updated["error_msg"], "OpenList API 调用失败")
        self.assertEqual(list_download_candidate_events(candidate["id"])[0]["action"], "process_failed")

    async def test_batch_processing_records_run_history(self):
        from database import list_candidate_process_runs, upsert_download_candidate
        from services.candidate_processor import process_candidates

        upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=15)):
            with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 15, "status": "downloading"}]):
                result = await process_candidates(
                    filters={"status": "candidate", "source": "subscription"},
                    policy="rules",
                    operator="manual",
                )

        runs = list_candidate_process_runs()
        self.assertEqual(result["run_id"], runs[0]["id"])
        self.assertEqual(runs[0]["policy"], "rules")
        self.assertEqual(runs[0]["sent"], 1)
        self.assertEqual(runs[0]["filters"]["source"], "subscription")

    async def test_preview_candidates_does_not_send_or_mutate(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import preview_candidates

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock()) as create:
            result = await preview_candidates(
                filters={"status": "candidate", "source": "subscription"},
                policy="rules",
            )

        create.assert_not_awaited()
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["counts"]["would_send"], 1)
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "candidate")

    async def test_process_candidates_respects_per_run_limit(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import process_candidates

        first = upsert_download_candidate(content_id="SIVR-438", title="A", source="subscription", magnet="magnet:a")
        second = upsert_download_candidate(content_id="ABP-588", title="B", source="subscription", magnet="magnet:b")

        with patch("config.Config.automation_max_auto_downloads_per_run", new_callable=PropertyMock, return_value=1):
            with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=31)) as create:
                with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 31, "status": "downloading"}]):
                    result = await process_candidates(
                        filters={"status": "candidate", "source": "subscription"},
                        policy="rules",
                        operator="manual",
                    )

        self.assertEqual(create.await_count, 1)
        self.assertEqual(result["counts"]["sent"], 1)
        self.assertEqual(result["counts"]["skipped_limit"], 1)
        self.assertEqual(get_download_candidate(first["id"])["status"], "sent")
        self.assertEqual(get_download_candidate(second["id"])["status"], "candidate")

    async def test_preview_candidates_reports_limit_without_mutating(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import preview_candidates

        first = upsert_download_candidate(content_id="SIVR-438", title="A", source="subscription", magnet="magnet:a")
        second = upsert_download_candidate(content_id="ABP-588", title="B", source="subscription", magnet="magnet:b")

        with patch("config.Config.automation_max_auto_downloads_per_run", new_callable=PropertyMock, return_value=1):
            result = await preview_candidates(
                filters={"status": "candidate", "source": "subscription"},
                policy="rules",
            )

        self.assertEqual(result["counts"]["would_send"], 1)
        self.assertEqual(result["counts"]["would_skip_limit"], 1)
        self.assertEqual(get_download_candidate(first["id"])["status"], "candidate")
        self.assertEqual(get_download_candidate(second["id"])["status"], "candidate")

    async def test_retry_failed_candidates_from_run_reprocesses_failed_ids(self):
        from database import get_download_candidate, list_candidate_process_runs, upsert_download_candidate
        from services.candidate_processor import process_candidates, retry_failed_candidates_from_run

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=21)):
            with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 21, "status": "failed", "error_msg": "OpenList failed"}]):
                failed = await process_candidates(
                    filters={"status": "candidate", "source": "subscription"},
                    policy="rules",
                    operator="manual",
                )

        self.assertEqual(get_download_candidate(candidate["id"])["status"], "failed")

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=22)):
            with patch("services.candidate_processor.get_download_tasks", return_value=[{"id": 22, "status": "downloading"}]):
                retried = await retry_failed_candidates_from_run(failed["run_id"], operator="manual")

        runs = list_candidate_process_runs()
        self.assertEqual(retried["source_run_id"], failed["run_id"])
        self.assertEqual(retried["total"], 1)
        self.assertEqual(retried["counts"]["sent"], 1)
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "sent")
        self.assertEqual(runs[0]["filters"]["source_run_id"], failed["run_id"])

    async def test_run_automatic_candidate_processing_records_manual_policy_run(self):
        from database import list_candidate_process_runs
        from services.candidate_processor import run_automatic_candidate_processing

        result = await run_automatic_candidate_processing(operator="manual")

        runs = list_candidate_process_runs()
        self.assertEqual(result["action"], "manual_policy")
        self.assertEqual(result["run_id"], runs[0]["id"])
        self.assertEqual(runs[0]["trigger_source"], "manual")
        self.assertEqual(runs[0]["policy"], "manual")

    async def test_run_automatic_candidate_processing_returns_busy_when_locked(self):
        from services import candidate_processor
        from services.candidate_processor import run_automatic_candidate_processing

        acquired = candidate_processor._PROCESSING_LOCK.acquire(blocking=False)
        self.assertTrue(acquired)
        try:
            result = await run_automatic_candidate_processing(operator="manual")
        finally:
            candidate_processor._PROCESSING_LOCK.release()

        self.assertEqual(result["status"], "busy")
        self.assertEqual(result["action"], "busy")

    async def test_list_candidates_includes_latest_event(self):
        from database import add_download_candidate_event, list_download_candidates, upsert_download_candidate

        candidate = upsert_download_candidate(content_id="SIVR-438", source="inventory")
        add_download_candidate_event(candidate["id"], "policy_skipped", "manual policy", "manual")

        rows = list_download_candidates(status="candidate", source="inventory")

        self.assertEqual(rows[0]["latest_event"]["action"], "policy_skipped")
        self.assertEqual(rows[0]["events"][0]["detail"], "manual policy")


class InventoryFillBehaviorTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fill_video_keeps_missing_fact_after_candidate_created(self):
        from database import add_missing_video, get_missing_videos, list_download_candidates
        from routers.inventory import fill_video

        add_missing_video("SIVR-438", 901, "Title", "2026-05-01", "")

        info_client = AsyncMock()
        info_client.get_video.return_value = {
            "content_id": "SIVR-438",
            "dvd_id": "SIVR-438",
            "title_ja": "Title",
            "release_date": "2026-05-01",
        }

        with patch("routers.inventory.get_info_client", return_value=info_client):
            result = await fill_video("SIVR-438")

        self.assertTrue(result["success"])
        self.assertEqual(len(get_missing_videos(901)), 1)
        candidates = list_download_candidates(source="inventory")
        self.assertEqual(candidates[0]["actress_id"], 901)

    async def test_fill_video_fallback_preserves_missing_actress_id(self):
        from database import add_missing_video, list_download_candidates
        from routers.inventory import fill_video

        add_missing_video("SIVR-438", 901, "Title", "2026-05-01", "")

        info_client = AsyncMock()
        info_client.get_video.side_effect = RuntimeError("javinfo unavailable")

        with patch("routers.inventory.get_info_client", return_value=info_client):
            result = await fill_video("SIVR-438")

        self.assertTrue(result["success"])
        candidates = list_download_candidates(source="inventory")
        self.assertEqual(candidates[0]["actress_id"], 901)
