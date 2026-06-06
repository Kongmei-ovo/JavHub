from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_support.client import ASGIClient, create_router_test_client


class SchedulerStatusRouteTest(unittest.TestCase):
    def _client(self) -> ASGIClient:
        from routers.scheduler import router

        return create_router_test_client(router)

    def test_scheduler_jobs_returns_registered_jobs_with_last_result(self):
        from scheduler import tasks

        next_run = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
        tasks.record_scheduler_job_result(
            "subscription_check",
            status="success",
            run_at=next_run,
            duration_ms=25,
            error=None,
        )
        jobs = [
            SimpleNamespace(id="subscription_check", name="订阅检查", next_run_time=next_run),
            SimpleNamespace(id="inventory_comparison", name="库存对比", next_run_time=None),
            SimpleNamespace(id="candidate_auto_process", name="候选自动处理", next_run_time=None),
        ]

        with patch.object(tasks.scheduler, "get_jobs", Mock(return_value=jobs)):
            response = self._client().get("/api/v1/scheduler/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {
                "id": "subscription_check",
                "name": "订阅检查",
                "next_run_time": "2026-06-06T12:00:00+00:00",
                "last_run_at": "2026-06-06T12:00:00+00:00",
                "last_duration_ms": 25,
                "last_status": "success",
                "last_error": None,
            },
            {
                "id": "inventory_comparison",
                "name": "库存对比",
                "next_run_time": None,
                "last_run_at": None,
                "last_duration_ms": None,
                "last_status": None,
                "last_error": None,
            },
            {
                "id": "candidate_auto_process",
                "name": "候选自动处理",
                "next_run_time": None,
                "last_run_at": None,
                "last_duration_ms": None,
                "last_status": None,
                "last_error": None,
            },
        ])

    def test_scheduler_job_wrapper_records_success_and_failure(self):
        from scheduler import tasks

        tasks.clear_scheduler_job_results()

        wrapped_success = tasks.scheduler_job_wrapper("ok_job", lambda: "ok")
        self.assertEqual(wrapped_success(), "ok")
        success_result = tasks.get_scheduler_job_result("ok_job")
        self.assertEqual(success_result["last_status"], "success")
        self.assertIsNotNone(success_result["last_run_at"])
        self.assertIsInstance(success_result["last_duration_ms"], int)
        self.assertIsNone(success_result["last_error"])

        def fail() -> None:
            raise RuntimeError("boom")

        wrapped_failure = tasks.scheduler_job_wrapper("failed_job", fail)
        with self.assertRaises(RuntimeError):
            wrapped_failure()
        failure_result = tasks.get_scheduler_job_result("failed_job")
        self.assertEqual(failure_result["last_status"], "failed")
        self.assertEqual(failure_result["last_error"], "boom")


if __name__ == "__main__":
    unittest.main()
