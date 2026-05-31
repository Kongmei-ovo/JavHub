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

    def test_variant_index_stats_uses_short_response_cache_with_bypass(self):
        client = create_router_test_client(router)

        with patch("routers.video_variant_index.variant_group_stats", side_effect=[
            {"group_count": 1, "item_count": 2},
            {"group_count": 3, "item_count": 4},
        ]) as stats:
            first = client.get("/api/v1/video-variants/index/stats")
            second = client.get("/api/v1/video-variants/index/stats")
            bypassed = client.get("/api/v1/video-variants/index/stats?cache=0")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(bypassed.status_code, 200)
        self.assertEqual(first.json()["group_count"], 1)
        self.assertEqual(second.json()["group_count"], 1)
        self.assertEqual(bypassed.json()["group_count"], 3)
        self.assertEqual(stats.call_count, 2)


if __name__ == "__main__":
    unittest.main()
