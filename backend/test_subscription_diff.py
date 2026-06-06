from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class SubscriptionDiffTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_check_report_only_marks_codes_new_once(self):
        from database import add_subscription, get_subscriptions, update_subscription
        from services.subscription import check_all_subscriptions_report

        sub_id = add_subscription(123, "Actor")
        update_subscription(sub_id, cadence_minutes=0)

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_actress = AsyncMock(return_value={
                "checked": 2,
                "created": 2,
                "existing": 0,
                "skipped": 0,
                "skipped_exempt": 0,
                "in_library": 0,
                "candidate_count": 2,
                "new_movies": [
                    {"candidate_id": 7, "dvd_id": "SIVR-438", "code": "SIVR-438"},
                    {"candidate_id": 8, "dvd_id": "ABP-588", "code": "ABP-588"},
                ],
            })

            first = await check_all_subscriptions_report()
            second = await check_all_subscriptions_report()

        self.assertEqual(first["new_since_last"], ["SIVR-438", "ABP-588"])
        self.assertEqual(first["results"][0]["new_since_last"], ["SIVR-438", "ABP-588"])
        self.assertEqual(first["new_found"], 2)
        self.assertEqual(second["new_since_last"], [])
        self.assertEqual(second["results"][0]["new_since_last"], [])
        self.assertEqual(second["new_found"], 0)
        self.assertEqual(pipeline.generate_candidates_for_actress.await_count, 2)

        row = get_subscriptions()[0]
        self.assertEqual(row["last_seen_codes"], ["SIVR-438", "ABP-588"])

    async def test_recent_success_skips_until_cadence_expires(self):
        from database import add_subscription
        from services.subscription import check_all_subscriptions_report

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_actress = AsyncMock(return_value={
                "checked": 1,
                "created": 1,
                "new_movies": [{"dvd_id": "SIVR-438"}],
            })

            first = await check_all_subscriptions_report()
            second = await check_all_subscriptions_report()

        self.assertEqual(first["subscriptions_checked"], 1)
        self.assertEqual(second["subscriptions_checked"], 0)
        self.assertEqual(second["subscriptions_skipped_cadence"], 1)
        self.assertEqual(second["results"][0]["skipped_reason"], "cadence")
        self.assertEqual(pipeline.generate_candidates_for_actress.await_count, 1)

    async def test_scheduled_subscription_check_honors_cadence(self):
        from database import add_subscription
        from services.subscription import check_all_subscriptions

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_actress = AsyncMock(return_value={
                "checked": 1,
                "created": 1,
                "new_movies": [{"dvd_id": "SIVR-438"}],
            })

            first = await check_all_subscriptions()
            second = await check_all_subscriptions()

        self.assertEqual([movie["dvd_id"] for movie in first], ["SIVR-438"])
        self.assertEqual(second, [])
        self.assertEqual(pipeline.generate_candidates_for_actress.await_count, 1)

    async def test_failure_sets_subscription_cooldown(self):
        from database import add_subscription, get_subscriptions
        from services.subscription import check_all_subscriptions_report

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_actress = AsyncMock(side_effect=RuntimeError("source down"))

            report = await check_all_subscriptions_report()

        self.assertEqual(report["subscriptions_checked"], 0)
        self.assertEqual(report["subscriptions_failed"], 1)
        self.assertEqual(report["results"][0]["error"], "source down")
        self.assertIsNotNone(get_subscriptions()[0]["cooldown_until"])


if __name__ == "__main__":
    unittest.main()
