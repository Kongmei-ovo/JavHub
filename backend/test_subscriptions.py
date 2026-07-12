from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class SubscriptionDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_new_subscription_exposes_cadence_and_diff_tracking_defaults(self):
        from database import add_subscription, get_subscriptions, update_subscription

        sub_id = add_subscription(101, "Tracked")

        row = get_subscriptions()[0]
        self.assertEqual(row["id"], sub_id)
        self.assertEqual(row["cadence_minutes"], 1440)
        self.assertIsNone(row["cooldown_until"])
        self.assertEqual(row["last_seen_codes"], [])
        self.assertIsNone(row["last_run_at"])

        update_subscription(sub_id, cadence_minutes=90)

        updated = get_subscriptions()[0]
        self.assertEqual(updated["cadence_minutes"], 90)

    def test_cleanup_removes_disabled_subscription_rows(self):
        from database import add_subscription, cleanup_legacy_subscriptions, get_subscriptions, update_subscription

        disabled_id = add_subscription(101, "Disabled")
        enabled_id = add_subscription(202, "Enabled")
        update_subscription(disabled_id, enabled=False)

        removed = cleanup_legacy_subscriptions()

        self.assertEqual(removed, 1)
        rows = get_subscriptions()
        self.assertEqual([row["id"] for row in rows], [enabled_id])
        self.assertEqual(rows[0]["actress_id"], 202)

    def test_toggle_existing_subscription_deletes_row(self):
        from database import add_subscription, get_subscriptions, is_subscribed, toggle_subscription

        add_subscription(101, "Subscribed")

        result = toggle_subscription(101, "Subscribed")

        self.assertEqual(result["subscribed"], False)
        self.assertFalse(is_subscribed(101))
        self.assertEqual(get_subscriptions(), [])


class SubscriptionServiceTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_run_subscription_check_annotates_movies_and_updates_last_check(self):
        from database import establish_baseline
        from services import subscription

        # Baseline already established → this is a subsequent check.
        establish_baseline(9, ["OLD-1"])
        pipeline = AsyncMock()
        pipeline.fetch_actress_videos = AsyncMock(return_value=[
            {"content_id": "SIVR-438", "dvd_id": "SIVR-438", "title": "T", "release_date": "2999-01-01"},
        ])
        sub = {"id": 9, "scope": "actress", "actress_id": 123, "actress_name": "Actor",
               "target_id": 123, "target_label": "Actor", "last_seen_codes": []}

        with patch.object(subscription, "start_acquisition", new=AsyncMock()) as start, \
             patch.object(subscription, "update_last_check") as update_last_check, \
             patch.object(subscription, "_subscription_auto_acquire_enabled", return_value=True), \
             patch("services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()):
            result = await subscription._run_subscription_check(sub, pipeline)

        pipeline.fetch_actress_videos.assert_awaited_once_with(123, info_semaphore=None)
        start.assert_awaited_once()  # fresh dated release auto-acquires
        self.assertEqual(result["new_movies"][0]["actress_name"], "Actor")
        self.assertEqual(result["new_movies"][0]["subscription_id"], 9)
        update_last_check.assert_called_once()
        self.assertEqual(update_last_check.call_args.args[:2], (9, "SIVR-438"))


class SubscriptionRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_subscription_accepts_cadence_minutes(self):
        from routers.subscriptions import UpdateSubscriptionRequest, update_subscription_endpoint

        with patch("database.update_subscription") as update_subscription:
            result = await update_subscription_endpoint(
                5,
                UpdateSubscriptionRequest(cadence_minutes=120),
            )

        self.assertEqual(result, {"status": "ok"})
        update_subscription.assert_called_once_with(5, cadence_minutes=120)


if __name__ == "__main__":
    unittest.main()
