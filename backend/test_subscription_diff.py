from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class SubscriptionDiffTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_check_report_only_marks_codes_new_once(self):
        from database import add_subscription, update_subscription
        from services.subscription import check_all_subscriptions_report

        sub_id = add_subscription(123, "Actor")
        update_subscription(sub_id, cadence_minutes=0)

        old = {"content_id": "OLD-1", "dvd_id": "OLD-1", "title": "o"}
        fresh = {"content_id": "NEW-1", "dvd_id": "NEW-1", "title": "n"}  # dateless → candidate

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
             patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()):
            pipeline = pipeline_cls.return_value
            pipeline.fetch_actress_videos = AsyncMock(side_effect=[
                [old],          # run 1 → baseline {OLD-1}, nothing "new"
                [old, fresh],   # run 2 → NEW-1 surfaces as new
                [old, fresh],   # run 3 → NEW-1 now folded into baseline
            ])

            first = await check_all_subscriptions_report()
            second = await check_all_subscriptions_report()
            third = await check_all_subscriptions_report()

        self.assertEqual(first["new_since_last"], [])  # first check only establishes baseline
        self.assertEqual(first["subscriptions_baselined"], 1)
        self.assertEqual(second["new_since_last"], ["NEW-1"])  # surfaced exactly once
        self.assertEqual(second["results"][0]["new_since_last"], ["NEW-1"])
        self.assertEqual(third["new_since_last"], [])
        self.assertEqual(pipeline.fetch_actress_videos.await_count, 3)

    async def test_recent_success_skips_until_cadence_expires(self):
        from database import add_subscription
        from services.subscription import check_all_subscriptions_report

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
             patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()):
            pipeline = pipeline_cls.return_value
            pipeline.fetch_actress_videos = AsyncMock(return_value=[
                {"content_id": "SIVR-438", "dvd_id": "SIVR-438", "title": "x"},
            ])

            first = await check_all_subscriptions_report()
            second = await check_all_subscriptions_report()

        self.assertEqual(first["subscriptions_checked"], 1)
        self.assertEqual(second["subscriptions_checked"], 0)
        self.assertEqual(second["subscriptions_skipped_cadence"], 1)
        self.assertEqual(second["results"][0]["skipped_reason"], "cadence")
        self.assertEqual(pipeline.fetch_actress_videos.await_count, 1)

    async def test_scheduled_subscription_check_honors_cadence(self):
        from database import add_subscription, establish_baseline
        from services.subscription import check_all_subscriptions

        sub_id = add_subscription(123, "Actor")
        establish_baseline(sub_id, ["OLD-1"])  # so the first run is a subsequent check

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
             patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()):
            pipeline = pipeline_cls.return_value
            pipeline.fetch_actress_videos = AsyncMock(return_value=[
                {"content_id": "OLD-1", "dvd_id": "OLD-1"},
                {"content_id": "SIVR-438", "dvd_id": "SIVR-438", "title": "x"},  # dateless → candidate
            ])

            first = await check_all_subscriptions()
            second = await check_all_subscriptions()

        self.assertEqual([movie["dvd_id"] for movie in first], ["SIVR-438"])
        self.assertEqual(second, [])
        self.assertEqual(pipeline.fetch_actress_videos.await_count, 1)

    async def test_failure_sets_subscription_cooldown(self):
        from database import add_subscription, get_subscriptions
        from services.subscription import check_all_subscriptions_report

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
             patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()):
            pipeline = pipeline_cls.return_value
            pipeline.fetch_actress_videos = AsyncMock(side_effect=RuntimeError("source down"))

            report = await check_all_subscriptions_report()

        self.assertEqual(report["subscriptions_checked"], 0)
        self.assertEqual(report["subscriptions_failed"], 1)
        self.assertEqual(report["results"][0]["error"], "source down")
        self.assertIsNotNone(get_subscriptions()[0]["cooldown_until"])


if __name__ == "__main__":
    unittest.main()
