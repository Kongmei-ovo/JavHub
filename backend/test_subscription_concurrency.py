from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.postgres import TempPostgresMixin


class SubscriptionConcurrencyTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_check_report_runs_subscriptions_concurrently(self):
        from services.subscription import check_all_subscriptions_report

        subscriptions = [
            {
                "id": index,
                "enabled": True,
                "scope": "actress",
                "actress_id": index,
                "actress_name": f"Actor {index}",
                "target_id": index,
                "target_label": f"Actor {index}",
                "last_seen_codes": [],
                "cadence_minutes": 0,
            }
            for index in range(1, 21)
        ]
        max_active = 0
        active = 0
        lock = asyncio.Lock()

        async def fetch_actress_videos(target_id, info_semaphore=None):
            nonlocal active, max_active
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            async with lock:
                active -= 1
            code = f"TEST-{target_id:03d}"
            return [{"content_id": code, "dvd_id": code, "title": "x"}]

        with patch("services.subscription.get_subscriptions", return_value=subscriptions), \
            patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
            patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()), \
            patch("services.subscription.update_last_check"):
            pipeline = pipeline_cls.return_value
            pipeline.fetch_actress_videos = AsyncMock(side_effect=fetch_actress_videos)

            started = time.perf_counter()
            report = await check_all_subscriptions_report()
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.45)
        self.assertGreater(max_active, 1)
        self.assertLessEqual(max_active, 8)
        self.assertEqual(report["subscriptions_checked"], 20)
        self.assertEqual(pipeline.fetch_actress_videos.await_count, 20)


if __name__ == "__main__":
    unittest.main()
