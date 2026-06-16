from __future__ import annotations

import unittest

from test_support.postgres import TempPostgresMixin


class SubscriptionBaselineTests(TempPostgresMixin, unittest.TestCase):
    def test_baseline_records_full_filmography_once(self):
        from database import (
            establish_baseline,
            filter_new_against_baseline,
            is_in_baseline,
        )

        established = establish_baseline(1, ["A-1", "A-2", "A-3"])
        self.assertTrue(established)
        self.assertTrue(is_in_baseline(1, "A-2"))
        self.assertFalse(is_in_baseline(1, "A-9"))

        new = filter_new_against_baseline(1, ["A-2", "A-4"])
        self.assertEqual(new, ["A-4"])  # baseline members are not "new"

    def test_establish_is_idempotent_and_does_not_overwrite(self):
        from database import establish_baseline, is_in_baseline

        self.assertTrue(establish_baseline(7, ["B-1"]))
        # A second establish must not wipe or re-seed the baseline.
        self.assertFalse(establish_baseline(7, ["B-2", "B-3"]))
        self.assertTrue(is_in_baseline(7, "B-1"))
        self.assertFalse(is_in_baseline(7, "B-2"))

    def test_baseline_is_not_capped_at_500(self):
        from database import establish_baseline, is_in_baseline

        establish_baseline(2, [f"X-{i}" for i in range(1200)])
        self.assertTrue(is_in_baseline(2, "X-1100"))  # old entries are never evicted

    def test_add_to_baseline_and_get_baseline_at(self):
        from database import add_to_baseline, get_baseline_at, is_in_baseline

        self.assertIsNone(get_baseline_at(3))  # no baseline yet

        from database import establish_baseline

        establish_baseline(3, ["C-1"])
        baseline_at = get_baseline_at(3)
        self.assertIsNotNone(baseline_at)

        add_to_baseline(3, "C-2")
        self.assertTrue(is_in_baseline(3, "C-2"))
        # Re-adding is a no-op, not an error.
        add_to_baseline(3, "C-2")
        self.assertTrue(is_in_baseline(3, "C-2"))


if __name__ == "__main__":
    unittest.main()
