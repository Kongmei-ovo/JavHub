from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from test_support.postgres import TempPostgresMixin


class CandidateProcessorTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_classify_candidate_error_maps_retry_metadata(self):
        from services import candidate_processor

        classify = getattr(candidate_processor, "classify_candidate_error", None)
        self.assertIsNotNone(classify, "classify_candidate_error should exist")
        if classify is None:
            return

        cases = [
            ("missing magnet", "missing_magnet", False),
            (TimeoutError("source request timed out"), "source_timeout", True),
            ("401 unauthorized from downloader", "downloader_auth", False),
            ("duplicate download task already exists", "duplicate", False),
            ("remote rejected task: invalid path", "remote_rejected", False),
            ("unexpected downloader response", "unknown", True),
        ]

        for error, category, retryable in cases:
            with self.subTest(category=category):
                metadata = classify(error)
                self.assertEqual(metadata["error_category"], category)
                self.assertIs(metadata["retryable"], retryable)

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
            with patch("services.candidate_processor.get_download_task", return_value={"id": 7, "status": "downloading"}):
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
                with patch("services.candidate_processor.get_download_task", return_value={"id": 9, "status": "downloading"}):
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
                with patch("services.candidate_processor.get_download_task", return_value={"id": 9, "status": "downloading"}):
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
            with patch("services.candidate_processor.get_download_task", return_value={"id": 12, "status": "failed", "error_msg": "OpenList API 调用失败"}):
                result = await process_candidate(candidate["id"], policy="rules")

        self.assertEqual(result["action"], "failed_downloader")
        updated = get_download_candidate(candidate["id"])
        self.assertEqual(updated["status"], "failed")
        self.assertEqual(updated["error_msg"], "OpenList API 调用失败")
        self.assertEqual(list_download_candidate_events(candidate["id"])[0]["action"], "process_failed")

    async def test_process_candidate_failure_includes_retry_metadata_in_result_and_event(self):
        from database import list_download_candidate_events, upsert_download_candidate
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:123",
        )

        with patch(
            "services.candidate_processor.downloader_service.create_download_task",
            new=AsyncMock(side_effect=PermissionError("401 unauthorized from downloader")),
        ):
            result = await process_candidate(candidate["id"], policy="rules")

        self.assertEqual(result["action"], "failed_downloader")
        self.assertEqual(result["error_category"], "downloader_auth")
        self.assertIs(result["retryable"], False)
        detail = json.loads(list_download_candidate_events(candidate["id"])[0]["detail"])
        self.assertEqual(detail["error_category"], "downloader_auth")
        self.assertIs(detail["retryable"], False)
        self.assertEqual(detail["error"], "401 unauthorized from downloader")

    async def test_batch_failure_records_retry_metadata_in_run_result(self):
        from database import list_candidate_process_runs, list_download_candidate_events, upsert_download_candidate
        from services.candidate_processor import process_candidates

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
        )

        result = await process_candidates(
            filters={"status": "candidate", "source": "subscription"},
            policy="auto",
            enrich=False,
            operator="manual",
        )

        self.assertEqual(result["results"][0]["action"], "failed_missing_magnet")
        self.assertEqual(result["results"][0]["error_category"], "missing_magnet")
        self.assertIs(result["results"][0]["retryable"], False)
        runs = list_candidate_process_runs()
        run_result = runs[0]["result"]["results"][0]
        self.assertEqual(run_result["error_category"], "missing_magnet")
        self.assertIs(run_result["retryable"], False)
        detail = json.loads(list_download_candidate_events(candidate["id"])[0]["detail"])
        self.assertEqual(detail["error_category"], "missing_magnet")
        self.assertIs(detail["retryable"], False)

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
            with patch("services.candidate_processor.get_download_task", return_value={"id": 15, "status": "downloading"}):
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
                with patch("services.candidate_processor.get_download_task", return_value={"id": 31, "status": "downloading"}):
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

    async def test_preview_candidates_respects_latest_event_action_filter(self):
        from database import add_download_candidate_event, upsert_download_candidate
        from services.candidate_processor import preview_candidates

        failed = upsert_download_candidate(content_id="SIVR-438", source="subscription")
        stale = upsert_download_candidate(content_id="ABP-588", source="subscription")
        add_download_candidate_event(failed["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "policy_skipped", "manual policy", "manual")

        result = await preview_candidates(
            filters={
                "status": "candidate",
                "needs_magnet": True,
                "latest_event_action": "magnet_enrich_failed",
            },
            policy="rules",
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["candidate"]["id"], failed["id"])
        self.assertEqual(result["counts"]["would_enrich_magnet"], 1)

    async def test_process_candidates_respects_missing_cover_filter(self):
        from database import get_download_candidate, upsert_download_candidate
        from services.candidate_processor import process_candidates

        missing = upsert_download_candidate(
            content_id="SIVR-438",
            source="supplement",
            jacket_thumb_url="",
            magnet="magnet:a",
        )
        upsert_download_candidate(
            content_id="ABP-588",
            source="supplement",
            jacket_thumb_url="https://example.com/cover.jpg",
            magnet="magnet:b",
        )

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=31)):
            with patch("services.candidate_processor.get_download_task", return_value={"id": 31, "status": "downloading"}):
                result = await process_candidates(
                    filters={"status": "candidate", "source": "supplement", "missing_cover": True},
                    policy="rules",
                    operator="manual",
                )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["counts"]["sent"], 1)
        self.assertEqual(get_download_candidate(missing["id"])["status"], "sent")

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
            with patch("services.candidate_processor.get_download_task", return_value={"id": 21, "status": "failed", "error_msg": "OpenList failed"}):
                failed = await process_candidates(
                    filters={"status": "candidate", "source": "subscription"},
                    policy="rules",
                    operator="manual",
                )

        self.assertEqual(get_download_candidate(candidate["id"])["status"], "failed")

        with patch("services.candidate_processor.downloader_service.create_download_task", new=AsyncMock(return_value=22)):
            with patch("services.candidate_processor.get_download_task", return_value={"id": 22, "status": "downloading"}):
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

    async def test_list_candidates_filters_by_latest_event_action(self):
        from database import add_download_candidate_event, list_download_candidates, upsert_download_candidate

        failed = upsert_download_candidate(content_id="SIVR-438", source="inventory")
        stale = upsert_download_candidate(content_id="ABP-588", source="inventory")
        add_download_candidate_event(failed["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "policy_skipped", "manual policy", "manual")

        rows = list_download_candidates(
            status="candidate",
            source="inventory",
            needs_magnet=True,
            latest_event_action="magnet_enrich_failed",
        )

        self.assertEqual([row["content_id"] for row in rows], ["SIVR-438"])
        self.assertEqual(rows[0]["latest_event"]["action"], "magnet_enrich_failed")

    async def test_list_candidates_page_filters_by_latest_event_action(self):
        from database import add_download_candidate_event, list_download_candidates_page, upsert_download_candidate

        failed = upsert_download_candidate(content_id="SIVR-438", source="inventory")
        stale = upsert_download_candidate(content_id="ABP-588", source="inventory")
        add_download_candidate_event(failed["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "magnet_enrich_failed", "no magnet found", "manual")
        add_download_candidate_event(stale["id"], "policy_skipped", "manual policy", "manual")

        page = list_download_candidates_page(
            status="candidate",
            source="inventory",
            needs_magnet=True,
            latest_event_action="magnet_enrich_failed",
            limit=10,
            offset=0,
        )

        self.assertEqual(page["total"], 1)
        self.assertEqual([row["content_id"] for row in page["data"]], ["SIVR-438"])

    async def test_list_candidates_page_latest_event_action_handles_empty_page(self):
        from database import list_download_candidates_page, upsert_download_candidate

        upsert_download_candidate(content_id="SIVR-438", source="inventory")

        page = list_download_candidates_page(
            status="candidate",
            source="inventory",
            needs_magnet=True,
            latest_event_action="magnet_enrich_failed",
            limit=10,
            offset=0,
        )

        self.assertEqual(page, {"data": [], "total": 0})

    async def test_list_candidates_page_filters_without_latest_event(self):
        from database import add_download_candidate_event, list_download_candidates_page, upsert_download_candidate

        without_event = upsert_download_candidate(content_id="SIVR-438", source="inventory")
        with_event = upsert_download_candidate(content_id="ABP-588", source="inventory")
        add_download_candidate_event(with_event["id"], "policy_skipped", "manual policy", "manual")

        page = list_download_candidates_page(
            status="candidate",
            source="inventory",
            needs_magnet=True,
            latest_event_action="without_event",
            limit=10,
            offset=0,
        )

        self.assertEqual(page["total"], 1)
        self.assertEqual([row["id"] for row in page["data"]], [without_event["id"]])

    async def test_list_candidates_page_filters_missing_cover(self):
        from database import list_download_candidates_page, upsert_download_candidate

        missing = upsert_download_candidate(
            content_id="SIVR-438",
            source="supplement",
            jacket_thumb_url="",
        )
        placeholder = upsert_download_candidate(
            content_id="ABP-588",
            source="supplement",
            jacket_thumb_url="https://example.com/noimage.jpg",
        )
        upsert_download_candidate(
            content_id="MIAA-999",
            source="supplement",
            jacket_thumb_url="https://example.com/cover.jpg",
        )

        page = list_download_candidates_page(
            status="candidate",
            source="supplement",
            missing_cover=True,
            limit=10,
            offset=0,
        )

        self.assertEqual(page["total"], 2)
        self.assertEqual([row["id"] for row in page["data"]], [missing["id"], placeholder["id"]])


class InventoryFillBehaviorTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
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
