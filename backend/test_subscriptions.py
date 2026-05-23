from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
