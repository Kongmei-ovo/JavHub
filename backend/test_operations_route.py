from __future__ import annotations

import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from test_support.cache import FakeRedisMixin


class OperationsRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    async def test_overview_uses_short_response_cache_for_expensive_dependencies(self):
        from routers import operations
        from services import cache

        client = SimpleNamespace(proxy_get=AsyncMock(side_effect=[
            {"total_jobs": 12},
            {"total": 3},
            {"total_count": 1},
            {
                "total": 2,
                "data": [
                    {"last_error": "javlibrary source is temporarily unavailable by source health control"},
                    {"last_error": "fanza: no high-confidence fanza candidate for MIAA-001"},
                    {"last_error": "mgstage request failed: 403 Forbidden"},
                ],
            },
        ]))
        captured: dict[str, object] = {}
        original_get_or_set = cache.get_or_set_response

        async def capture_cache(namespace, params, producer, ttl=cache.DEFAULT_RESPONSE_TTL):
            captured.update({"namespace": namespace, "params": params, "ttl": ttl})
            return await original_get_or_set(namespace, params, producer, ttl=ttl)

        with patch.object(operations, "config", SimpleNamespace(
            automation={"enabled": True},
            actor_mapping={"enabled": False},
        )), \
            patch.object(operations, "get_latest_snapshot_key", Mock(return_value="snap-1")) as latest, \
            patch.object(operations, "count_snapshot_actors", Mock(return_value=2)) as actor_count, \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 7})) as candidates, \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[
                {"id": 10, "status": "running"},
                {"id": 11, "status": "failed"},
            ])) as jobs, \
            patch.object(operations, "missing_videos_summary", Mock(return_value={
                "total": 2,
                "top_actresses": [{"actress_id": 1, "actress_name": "A", "missing_count": 2}],
            })) as missing, \
            patch.object(operations, "variant_group_stats", Mock(return_value={"groups": 4})) as variant_stats, \
            patch.object(operations, "build_data_quality_overview", Mock(return_value={
                "status": "ok",
                "summary": {"total_issues": 0},
                "issues": [],
            })) as data_quality, \
            patch.object(operations, "mapping_summary_for_snapshot", Mock(return_value={"mapped": 2})) as mapping, \
            patch.object(operations, "list_candidate_process_runs", Mock(return_value=[{"id": 5}])) as runs, \
            patch.object(operations, "_candidate_schedule_state", Mock(return_value={
                "enabled": True,
                "policy": "rules",
                "effective_enabled": True,
                "disabled_reason": "",
            })) as schedule, \
            patch("modules.info_client.get_info_client", Mock(return_value=client)), \
            patch.object(operations.cache, "get_or_set_response", capture_cache):
            first = await operations.operations_overview()
            second = await operations.operations_overview()

        self.assertEqual(first, second)
        self.assertEqual(captured, {"namespace": "operations_overview", "params": {}, "ttl": 15})
        self.assertEqual(latest.call_count, 1)
        actor_count.assert_called_once_with("snap-1")
        candidates.assert_called_once()
        jobs.assert_called_once_with(limit=10)
        missing.assert_called_once_with(limit=8)
        variant_stats.assert_called_once()
        data_quality.assert_called_once_with(
            limit=8,
            repair_progress={
                "low_quality_cover": {
                    "available": True,
                    "queued": 3,
                    "running": 1,
                    "failed": 2,
                    "failed_reasons": [
                        {"label": "来源暂不可用", "count": 1},
                        {"label": "低置信匹配", "count": 1},
                        {"label": "请求失败", "count": 1},
                    ],
                    "provider_failures": [
                        {"provider": "fanza", "count": 1},
                        {"provider": "javlibrary", "count": 1},
                        {"provider": "mgstage", "count": 1},
                    ],
                },
            },
        )
        mapping.assert_called_once_with("snap-1")
        runs.assert_called_once_with(limit=5)
        schedule.assert_called_once()
        self.assertEqual(client.proxy_get.await_count, 4)
        self.assertEqual(first["snapshot"]["actor_count"], 2)
        self.assertEqual(first["missing"]["total"], 2)
        self.assertEqual(first["missing"]["top_actresses"][0]["missing_count"], 2)
        self.assertEqual(first["supplement"], {
            "available": True,
            "stats": {"total_jobs": 12},
            "queued": 3,
            "running": 1,
            "failed": 2,
            "failed_samples": [
                {"last_error": "javlibrary source is temporarily unavailable by source health control"},
                {"last_error": "fanza: no high-confidence fanza candidate for MIAA-001"},
                {"last_error": "mgstage request failed: 403 Forbidden"},
            ],
        })

    async def test_overview_fetches_supplement_statuses_concurrently(self):
        from routers import operations

        started: list[tuple[str, str | None]] = []
        all_started = asyncio.Event()
        counts = {"queued": 3, "running": 1, "failed": 2}

        async def proxy_get(path, params=None):
            status = (params or {}).get("status")
            started.append((path, status))
            if len(started) == 4:
                all_started.set()
            await asyncio.wait_for(all_started.wait(), timeout=0.1)
            if path == "/api/v1/supplement/stats":
                return {"total_jobs": 12}
            return {"total": counts[status]}

        client = SimpleNamespace(proxy_get=AsyncMock(side_effect=proxy_get))

        with patch.object(operations, "config", SimpleNamespace(
            automation={"enabled": True},
            actor_mapping={"enabled": True},
        )), \
            patch.object(operations, "get_latest_snapshot_key", Mock(return_value=None)), \
            patch.object(operations, "count_snapshot_actors", Mock(return_value=0)), \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 0})), \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[])), \
            patch.object(operations, "missing_videos_summary", Mock(return_value={"total": 0, "top_actresses": []})), \
            patch.object(operations, "variant_group_stats", Mock(return_value={"groups": 0})), \
            patch.object(operations, "build_data_quality_overview", Mock(return_value={
                "status": "ok",
                "summary": {"total_issues": 0},
                "issues": [],
            })), \
            patch.object(operations, "mapping_summary_for_snapshot", Mock(return_value={"mapped": 0})), \
            patch.object(operations, "list_candidate_process_runs", Mock(return_value=[])), \
            patch.object(operations, "_candidate_schedule_state", Mock(return_value={
                "enabled": True,
                "policy": "rules",
                "effective_enabled": True,
                "disabled_reason": "",
            })), \
            patch("modules.info_client.get_info_client", Mock(return_value=client)):
            result = await operations.operations_overview(cache_control="0")

        self.assertEqual(
            started,
            [
                ("/api/v1/supplement/stats", None),
                ("/api/v1/supplement/jobs", "queued"),
                ("/api/v1/supplement/jobs", "running"),
                ("/api/v1/supplement/jobs", "failed"),
            ],
        )
        self.assertEqual(result["supplement"], {
            "available": True,
            "stats": {"total_jobs": 12},
            "queued": 3,
            "running": 1,
            "failed": 2,
        })

    async def test_failed_job_provider_breakdown_counts_compound_errors(self):
        from services import supplement_repair_progress

        samples = [
            {
                "source": "all",
                "last_error": (
                    "partial retryable detail failures: avbase: avbase request failed: 404 Not Found; "
                    "fanza: no high-confidence fanza candidate for MIAA-001; "
                    "javlibrary: javlibrary cloudflare challenge returned; "
                    "mgstage: mgstage source is temporarily unavailable by source health control"
                ),
            },
            {
                "source": "all",
                "last_error": (
                    "partial retryable detail failures: avbase: avbase request failed: 404 Not Found; "
                    "fanza: no high-confidence fanza candidate for MIAA-002"
                ),
            },
            {"source": "javlibrary", "last_error": "javlibrary source is temporarily unavailable by source health control"},
        ]

        self.assertEqual(supplement_repair_progress.failed_job_providers(samples), [
            {"provider": "avbase", "count": 2, "route_source": "all"},
            {"provider": "fanza", "count": 2, "route_source": "all"},
            {"provider": "javlibrary", "count": 2, "route_source": "all"},
            {"provider": "mgstage", "count": 1, "route_source": "all"},
        ])

    async def test_overview_caches_supplement_fallback_when_info_client_fails(self):
        from routers import operations

        with patch.object(operations, "config", SimpleNamespace(
            automation={"enabled": False},
            actor_mapping={"enabled": True},
        )), \
            patch.object(operations, "get_latest_snapshot_key", Mock(return_value=None)) as latest, \
            patch.object(operations, "count_snapshot_actors", Mock(return_value=0)) as actor_count, \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 0})) as candidates, \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[])) as jobs, \
            patch.object(operations, "missing_videos_summary", Mock(return_value={"total": 0, "top_actresses": []})) as missing, \
            patch.object(operations, "variant_group_stats", Mock(return_value={"groups": 0})) as variant_stats, \
            patch.object(operations, "build_data_quality_overview", Mock(return_value={
                "status": "ok",
                "summary": {"total_issues": 0},
                "issues": [],
            })) as data_quality, \
            patch.object(operations, "mapping_summary_for_snapshot", Mock(return_value={"mapped": 0})) as mapping, \
            patch.object(operations, "list_candidate_process_runs", Mock(return_value=[])) as runs, \
            patch.object(operations, "_candidate_schedule_state", Mock(return_value={
                "enabled": False,
                "policy": "manual",
                "effective_enabled": False,
                "disabled_reason": "manual_policy",
            })) as schedule, \
            patch("modules.info_client.get_info_client", Mock(side_effect=RuntimeError("javinfo down"))) as info_client:
            first = await operations.operations_overview()
            second = await operations.operations_overview()

        self.assertEqual(first, second)
        self.assertEqual(first["supplement"], {"available": False, "error": "javinfo down"})
        self.assertEqual(latest.call_count, 1)
        actor_count.assert_called_once_with(None)
        candidates.assert_called_once()
        jobs.assert_called_once_with(limit=10)
        missing.assert_called_once_with(limit=8)
        variant_stats.assert_called_once()
        data_quality.assert_called_once_with(limit=8)
        mapping.assert_called_once_with(None)
        runs.assert_called_once_with(limit=5)
        schedule.assert_called_once()
        info_client.assert_called_once()

    async def test_candidate_schedule_state_marks_manual_policy_not_effective(self):
        from routers import operations

        scheduler_state = {
            "enabled": True,
            "running": False,
            "next_run_time": "2026-05-21T12:00:00",
        }

        with patch.object(operations, "config", SimpleNamespace(automation_download_policy="manual")), \
            patch("scheduler.tasks.candidate_auto_process_schedule_state", Mock(return_value=scheduler_state)):
            result = operations._candidate_schedule_state()

        self.assertEqual(result, {
            "enabled": True,
            "running": False,
            "next_run_time": "2026-05-21T12:00:00",
            "policy": "manual",
            "effective_enabled": False,
            "disabled_reason": "manual_policy",
        })

    async def test_candidate_run_now_exposes_manual_policy_noop(self):
        from routers import operations

        manual_result = {
            "status": "ok",
            "action": "manual_policy",
            "skipped": True,
            "reason": "manual policy",
            "total": 0,
            "counts": {},
            "results": [],
        }

        with patch("services.candidate_processor.run_automatic_candidate_processing", new=AsyncMock(return_value=manual_result)):
            result = await operations.run_candidate_processing_now()

        self.assertEqual(result, {
            **manual_result,
            "dry_run": False,
            "manual_noop": True,
            "effective": False,
        })
