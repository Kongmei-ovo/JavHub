from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from test_support.client import create_authed_router_test_client


class SchedulerRunRouteTests(unittest.TestCase):
    def _client(self):
        from routers.scheduler import router

        return create_authed_router_test_client(router)

    def test_unknown_job_returns_404(self):
        client = self._client()
        resp = client.post("/api/v1/scheduler/jobs/not_a_job/run")
        self.assertEqual(resp.status_code, 404)

    def test_known_job_triggers_func_in_background(self):
        from scheduler import tasks

        ran = threading.Event()

        def stub():
            ran.set()

        # Replace the whitelist with a single stub so we don't run real work.
        with patch.dict(tasks._MANUAL_JOB_FUNCS, {"variant_index_rebuild": stub}, clear=True):
            client = self._client()
            resp = client.post("/api/v1/scheduler/jobs/variant_index_rebuild/run")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("accepted"))
        self.assertTrue(ran.wait(timeout=2), "job function should run in the background")

    def test_already_running_job_is_not_double_fired(self):
        from scheduler import tasks

        release = threading.Event()

        def blocking():
            release.wait(timeout=2)

        with patch.dict(tasks._MANUAL_JOB_FUNCS, {"variant_index_rebuild": blocking}, clear=True):
            client = self._client()
            first = client.post("/api/v1/scheduler/jobs/variant_index_rebuild/run")
            second = client.post("/api/v1/scheduler/jobs/variant_index_rebuild/run")
            release.set()

        self.assertTrue(first.json().get("accepted"))
        self.assertFalse(second.json().get("accepted"))
        self.assertTrue(second.json().get("running"))

    def test_manual_job_drain_uses_one_shared_deadline(self):
        from scheduler import tasks

        release = threading.Event()
        threads = [
            threading.Thread(target=release.wait, name=f"manual-blocked-{index}", daemon=True)
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        try:
            with tasks._manual_run_lock:
                tasks._manual_run_threads.update({
                    f"blocked-{index}": thread for index, thread in enumerate(threads)
                })
            started = time.monotonic()
            with self.assertLogs("scheduler.tasks", level="WARNING") as captured:
                alive = tasks.drain_manual_scheduler_jobs(timeout=0.2)
            elapsed = time.monotonic() - started

            self.assertLess(elapsed, 0.32)
            self.assertEqual(set(alive), {thread.name for thread in threads})
            self.assertTrue(all(name in "\n".join(captured.output) for name in alive))
        finally:
            release.set()
            for thread in threads:
                thread.join(timeout=1)
            with tasks._manual_run_lock:
                for index in range(2):
                    tasks._manual_run_threads.pop(f"blocked-{index}", None)

    def test_manual_job_drain_returns_empty_after_threads_finish(self):
        from scheduler import tasks

        release = threading.Event()
        threads = [
            threading.Thread(target=release.wait, name=f"manual-finished-{index}", daemon=True)
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        with tasks._manual_run_lock:
            tasks._manual_run_threads.update({
                f"finished-{index}": thread for index, thread in enumerate(threads)
            })
        release.set()
        try:
            self.assertEqual(tasks.drain_manual_scheduler_jobs(timeout=1), ())
        finally:
            for thread in threads:
                thread.join(timeout=1)
            with tasks._manual_run_lock:
                for index in range(2):
                    tasks._manual_run_threads.pop(f"finished-{index}", None)


if __name__ == "__main__":
    unittest.main()
