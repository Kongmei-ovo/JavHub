from __future__ import annotations

import unittest
from unittest.mock import patch

from routers.video_variant_index import router
from test_support.client import create_router_test_client
from test_support.postgres import TempPostgresMixin


class VideoVariantIndexRouterTest(TempPostgresMixin, unittest.TestCase):
    def test_variant_index_job_routes_and_stats(self):
        with patch("routers.video_variant_index.start_variant_index_job") as start_job:
            start_job.return_value = {"id": 1, "status": "queued"}
            created = create_router_test_client(router).post("/api/v1/video-variants/index/jobs")

        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["id"], 1)
        self.assertEqual(created.json()["status"], "queued")

        client = create_router_test_client(router)
        jobs = client.get("/api/v1/video-variants/index/jobs")
        stats = client.get("/api/v1/video-variants/index/stats")

        self.assertEqual(jobs.status_code, 200)
        self.assertIn("data", jobs.json())
        self.assertEqual(stats.status_code, 200)
        self.assertIn("group_count", stats.json())


if __name__ == "__main__":
    unittest.main()
