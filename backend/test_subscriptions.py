from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class SubscriptionDatabaseTest(TempPostgresMixin, unittest.TestCase):
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


class SubscriptionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_subscription_check_annotates_movies_and_updates_last_check(self):
        from services.subscription import _run_subscription_check

        pipeline = AsyncMock()
        pipeline.generate_candidates_for_actress = AsyncMock(return_value={
            "created": 1,
            "new_movies": [
                {"candidate_id": 7, "dvd_id": "SIVR-438"},
                {"candidate_id": 8, "dvd_id": "ABP-588"},
            ],
        })
        sub = {"id": 9, "actress_id": 123, "actress_name": "Actor"}

        with patch("services.subscription.update_last_check") as update_last_check:
            result = await _run_subscription_check(sub, pipeline)

        pipeline.generate_candidates_for_actress.assert_awaited_once_with(
            actress_id=123,
            actress_name="Actor",
            trigger_source="subscription",
            reason="subscription_check",
        )
        self.assertEqual(result["new_movies"][0]["actress_name"], "Actor")
        self.assertEqual(result["new_movies"][0]["subscription_id"], 9)
        update_last_check.assert_called_once_with(9, "SIVR-438")


if __name__ == "__main__":
    unittest.main()
