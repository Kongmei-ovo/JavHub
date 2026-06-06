from __future__ import annotations

import json
import math
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

    async def test_magnet_score_returns_named_breakdown(self):
        from services.candidate_processor import _magnet_score

        score = _magnet_score(
            {
                "title": "SIVR-438 字幕 1080p",
                "size": "4.2GB",
                "hd": True,
                "subtitle": True,
                "resolution": "1080p",
                "quality": "HD",
            }
        )

        self.assertEqual(score["subtitle"], 1)
        self.assertEqual(score["hd"], 1)
        self.assertEqual(score["resolution"], 3)
        self.assertEqual(score["size_mb"], 4.2 * 1024)
        self.assertAlmostEqual(score["total"], 1000 + 100 + 30 + math.log2(1 + 4.2 * 1024))

    async def test_find_best_magnet_returns_ranked_score_breakdown(self):
        from services.candidate_processor import find_best_magnet

        subtitle_result = {
            "magnet": "magnet:?xt=urn:btih:sub",
            "title": "SIVR-438 字幕 720p",
            "size": "1.0GB",
            "source": "javdb",
            "subtitle": True,
            "resolution": "720p",
        }
        large_result = {
            "magnet": "magnet:?xt=urn:btih:large",
            "title": "SIVR-438 2160p",
            "size": "10.0GB",
            "source": "javbus",
            "resolution": "2160p",
            "hd": True,
        }

        with patch("services.candidate_processor.register_all_sources"):
            with patch(
                "services.candidate_processor.SourceRegistry.search_all",
                new=AsyncMock(return_value=[large_result, subtitle_result]),
            ):
                result = await find_best_magnet({"content_id": "SIVR-438"})

        self.assertEqual(result["best"]["magnet"], "magnet:?xt=urn:btih:sub")
        self.assertEqual(result["best"]["reason_breakdown"]["subtitle"], 1)
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["item"]["magnet"], "magnet:?xt=urn:btih:sub")
        self.assertGreater(result["candidates"][0]["score"]["total"], result["candidates"][1]["score"]["total"])

    async def test_find_best_magnet_returns_sanitized_top_five_alternatives(self):
        from services.candidate_processor import find_best_magnet

        source_results = [
            {
                "magnet": f"magnet:?xt=urn:btih:{idx}",
                "title": f"SIVR-438 {idx} 1080p",
                "source": "javdb",
                "size": f"{idx + 1}.0GB",
                "binary": b"torrent bytes",
            }
            for idx in range(6)
        ]

        with patch("services.candidate_processor.register_all_sources"):
            with patch(
                "services.candidate_processor.SourceRegistry.search_all",
                new=AsyncMock(return_value=source_results),
            ):
                result = await find_best_magnet({"content_id": "SIVR-438"})

        self.assertEqual(len(result["alternatives"]), 5)
        self.assertEqual(
            list(result["alternatives"][0].keys()),
            ["magnet", "source", "title", "score"],
        )
        self.assertNotIn("binary", result["alternatives"][0])
        self.assertEqual(result["best"]["magnet"], result["alternatives"][0]["magnet"])

    async def test_enrich_candidate_magnet_persists_score_and_records_json_detail(self):
        from database import get_download_candidate, list_download_candidate_events, upsert_download_candidate
        from services.candidate_processor import enrich_candidate_magnet

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            title="Title",
            source="inventory",
        )
        item = {
            "magnet": "magnet:?xt=urn:btih:456",
            "title": "SIVR-438 字幕 1080p",
            "size": "4.2GB",
            "source": "javdb",
            "subtitle": True,
            "hd": True,
            "resolution": "1080p",
        }
        score = {
            "best": {
                **item,
                "reason_breakdown": {
                    "subtitle": 1,
                    "hd": 1,
                    "resolution": 3,
                    "size_mb": 4300.8,
                    "total": 1142.071,
                },
            },
            "candidates": [
                {
                    "item": item,
                    "score": {
                        "subtitle": 1,
                        "hd": 1,
                        "resolution": 3,
                        "size_mb": 4300.8,
                        "total": 1142.071,
                    },
                }
            ],
        }

        with patch("services.candidate_processor.find_best_magnet", new=AsyncMock(return_value=score)):
            result = await enrich_candidate_magnet(candidate["id"], operator="manual")

        updated = get_download_candidate(candidate["id"])
        self.assertEqual(result["action"], "magnet_enriched")
        self.assertEqual(updated["magnet"], "magnet:?xt=urn:btih:456")
        self.assertEqual(updated["magnet_score"], score)
        self.assertEqual(updated["magnet_alternatives"][0]["magnet"], "magnet:?xt=urn:btih:456")
        detail = json.loads(list_download_candidate_events(candidate["id"])[0]["detail"])
        self.assertEqual(detail["source"], "javdb")
        self.assertEqual(detail["score"], score)

    async def test_process_candidate_retries_once_with_next_alternative_after_downloader_failure(self):
        from database import get_download_candidate, list_download_candidate_events, upsert_download_candidate
        from database.download_candidate import update_download_candidate_magnet_alternatives
        from services.candidate_processor import process_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="subscription",
            magnet="magnet:?xt=urn:btih:first",
            magnet_source="javdb",
        )
        update_download_candidate_magnet_alternatives(
            candidate["id"],
            [
                {"magnet": "magnet:?xt=urn:btih:first", "source": "javdb", "title": "First", "score": {"total": 20}},
                {"magnet": "magnet:?xt=urn:btih:second", "source": "javbus", "title": "Second", "score": {"total": 19}},
            ],
        )

        create = AsyncMock(side_effect=[11, 12])

        def task_for(task_id):
            if task_id == 11:
                return {"id": 11, "status": "failed", "error_msg": "remote rejected first magnet"}
            return {"id": 12, "status": "downloading"}

        with patch("services.candidate_processor.downloader_service.create_download_task", new=create):
            with patch("services.candidate_processor.get_download_task", side_effect=task_for):
                result = await process_candidate(candidate["id"], policy="rules")

        updated = get_download_candidate(candidate["id"])
        self.assertEqual(result["action"], "sent")
        self.assertEqual(result["download_task_id"], 12)
        self.assertEqual(updated["status"], "sent")
        self.assertEqual(updated["magnet"], "magnet:?xt=urn:btih:second")
        self.assertEqual(create.await_args_list[0].kwargs["magnet"], "magnet:?xt=urn:btih:first")
        self.assertEqual(create.await_args_list[1].kwargs["magnet"], "magnet:?xt=urn:btih:second")
        fallback_events = [event for event in list_download_candidate_events(candidate["id"]) if event["action"] == "magnet_fallback"]
        self.assertEqual(len(fallback_events), 1)
        detail = json.loads(fallback_events[0]["detail"])
        self.assertEqual(detail["from"], "magnet:?xt=urn:btih:first")
        self.assertEqual(detail["to"], "magnet:?xt=urn:btih:second")

    async def test_list_candidates_endpoint_exposes_magnet_score(self):
        from database import update_download_candidate_magnet, upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="inventory",
        )
        score = {
            "best": {"magnet": "magnet:?xt=urn:btih:456", "reason_breakdown": {"total": 1142.071}},
            "candidates": [{"item": {"magnet": "magnet:?xt=urn:btih:456"}, "score": {"total": 1142.071}}],
        }
        update_download_candidate_magnet(
            candidate["id"],
            "magnet:?xt=urn:btih:456",
            "javdb",
            score=score,
        )

        result = await downloads.list_candidates(source="inventory", limit=1, cache_control="no-cache")

        self.assertEqual(result["data"][0]["magnet_score"], score)

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

        self.assertEqual(result["best"]["download_url"], "https://indexer.test/download/SIVR-438.torrent")
        self.assertEqual(result["best"]["torrent_url"], "https://indexer.test/download/SIVR-438.torrent")
        self.assertEqual(result["candidates"][0]["score"]["resolution"], 3)

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
