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

    async def test_pipeline_uses_existing_codes_without_calling_emby_check_exists(self):
        from services.watchlist_pipeline import WatchlistPipeline

        info_client = AsyncMock()
        info_client.get_actress_videos.return_value = {
            "data": [
                {"content_id": "lib001", "dvd_id": "LIB-001", "title": "Already owned"},
                {"content_id": "miss002", "dvd_id": "MISS-002", "title": "Missing"},
            ]
        }
        emby_client = AsyncMock()
        emby_client.check_exists.side_effect = AssertionError("check_exists should not be called")

        pipeline = WatchlistPipeline(info_client=info_client, emby_client=emby_client)
        with patch("services.watchlist_pipeline.download_candidate_content_keys", Mock(return_value=set())), \
            patch("services.watchlist_pipeline.is_video_exempt", Mock(return_value=False)), \
            patch("services.watchlist_pipeline.upsert_candidate_from_video", Mock(return_value={
                "id": 9,
                "content_id": "MISS-002",
                "dvd_id": "MISS-002",
                "title": "Missing",
            })):
            result = await pipeline.generate_candidates_for_actress(
                123,
                "Actor",
                "subscription",
                existing_codes={"LIB001"},
            )

        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["in_library"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual([movie["dvd_id"] for movie in result["new_movies"]], ["MISS-002"])
        emby_client.check_exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
