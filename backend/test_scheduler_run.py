from __future__ import annotations

import threading
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


if __name__ == "__main__":
    unittest.main()
