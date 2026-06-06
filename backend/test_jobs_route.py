from __future__ import annotations

import unittest

from test_support.client import ASGIClient, create_router_test_client
from test_support.postgres import TempPostgresMixin


class JobsRouteTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    def _client(self) -> ASGIClient:
        from routers.jobs import router

        return create_router_test_client(router)

    def test_list_jobs_filters_by_kind_and_status(self):
        from database import create_job, update_job

        inventory_id = create_job("inventory", label="Collect")
        subscription_id = create_job("subscription", label="Nightly")
        update_job(inventory_id, status="running", progress=25)
        update_job(subscription_id, status="failed", progress=10)

        response = self._client().get(
            "/api/v1/jobs",
            params={"kind": "inventory", "status": "running", "limit": 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            {
                **response.json()["data"][0],
                "id": inventory_id,
                "kind": "inventory",
                "label": "Collect",
                "status": "running",
                "progress": 25,
            }
        ])

    def test_get_job_returns_single_row(self):
        from database import create_job

        job_id = create_job("subscription", label="Refresh actress")

        response = self._client().get(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], job_id)
        self.assertEqual(response.json()["kind"], "subscription")
        self.assertEqual(response.json()["label"], "Refresh actress")

    def test_cancel_marks_non_terminal_job_canceled(self):
        from database import create_job, get_job

        job_id = create_job("inventory")

        response = self._client().post(f"/api/v1/jobs/{job_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "canceled")
        self.assertEqual(get_job(job_id)["status"], "canceled")

    async def test_stream_connects_and_yields_progress_changes(self):
        from database import create_job, update_job
        from routers.jobs import stream_jobs

        job_id = create_job("inventory", label="Streaming")
        response = stream_jobs(poll_seconds=0.01)

        first = await self._next_data_event(response)
        update_job(job_id, status="running", progress=42)
        second = await self._next_data_event(response)
        await response.body_iterator.aclose()

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertIn(f'"id": {job_id}', first.decode())
        self.assertIn('"progress": 0', first.decode())
        self.assertIn(f'"id": {job_id}', second.decode())
        self.assertIn('"progress": 42', second.decode())

    async def test_stream_started_empty_yields_job_created_later(self):
        from database import create_job, update_job
        from routers.jobs import stream_jobs

        response = stream_jobs(kind="created-later", poll_seconds=0.01)

        heartbeat = await anext(response.body_iterator)
        job_id = create_job("created-later", label="Late arrival")
        first = await self._next_data_event(response)
        update_job(job_id, status="running", progress=88)
        second = await self._next_data_event(response)
        await response.body_iterator.aclose()

        self.assertEqual(heartbeat, b": keep-alive\n\n")
        self.assertIn(f'"id": {job_id}', first.decode())
        self.assertIn('"progress": 0', first.decode())
        self.assertIn(f'"id": {job_id}', second.decode())
        self.assertIn('"progress": 88', second.decode())

    async def _next_data_event(self, response):
        while True:
            chunk = await anext(response.body_iterator)
            if chunk.startswith(b"data: "):
                return chunk


if __name__ == "__main__":
    unittest.main()
