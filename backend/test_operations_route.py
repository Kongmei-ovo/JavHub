from __future__ import annotations

import unittest
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
            {"total": 2},
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
            patch.object(operations, "get_snapshot_actors", Mock(return_value={
                "data": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            })) as actors, \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 7})) as candidates, \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[
                {"id": 10, "status": "running"},
                {"id": 11, "status": "failed"},
            ])) as jobs, \
            patch.object(operations, "get_all_missing_videos", Mock(return_value=[
                {"actress_id": 1, "actress_name": "A"},
                {"actress_id": 1, "actress_name": "A"},
            ])) as missing, \
            patch.object(operations, "variant_group_stats", Mock(return_value={"groups": 4})) as variant_stats, \
            patch.object(operations, "mapping_summary", Mock(return_value={"mapped": 2})) as mapping, \
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
        actors.assert_called_once_with("snap-1", page_size=100000)
        candidates.assert_called_once()
        jobs.assert_called_once_with(limit=10)
        missing.assert_called_once()
        variant_stats.assert_called_once()
        mapping.assert_called_once()
        runs.assert_called_once_with(limit=5)
        schedule.assert_called_once()
        self.assertEqual(client.proxy_get.await_count, 4)
        self.assertEqual(first["supplement"], {
            "available": True,
            "stats": {"total_jobs": 12},
            "queued": 3,
            "running": 1,
            "failed": 2,
        })

    async def test_overview_caches_supplement_fallback_when_info_client_fails(self):
        from routers import operations

        with patch.object(operations, "config", SimpleNamespace(
            automation={"enabled": False},
            actor_mapping={"enabled": True},
        )), \
            patch.object(operations, "get_latest_snapshot_key", Mock(return_value=None)) as latest, \
            patch.object(operations, "get_snapshot_actors", Mock()) as actors, \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 0})) as candidates, \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[])) as jobs, \
            patch.object(operations, "get_all_missing_videos", Mock(return_value=[])) as missing, \
            patch.object(operations, "variant_group_stats", Mock(return_value={"groups": 0})) as variant_stats, \
            patch.object(operations, "mapping_summary", Mock(return_value={"mapped": 0})) as mapping, \
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
        actors.assert_not_called()
        candidates.assert_called_once()
        jobs.assert_called_once_with(limit=10)
        missing.assert_called_once()
        variant_stats.assert_called_once()
        mapping.assert_called_once_with([])
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
