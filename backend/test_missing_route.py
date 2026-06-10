from __future__ import annotations

import unittest
from unittest.mock import patch

from test_support.cache import FakeRedisMixin
from test_support.postgres import TempPostgresMixin


class MissingRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    async def test_list_missing_actresses_uses_short_response_cache_with_bypass(self):
        from routers import missing

        with patch.object(missing, "list_missing_actresses_from_inventory", side_effect=[
            [{"actress_id": 1, "missing_count": 2}],
            [{"actress_id": 2, "missing_count": 3}],
        ]) as summaries:
            first = await missing.list_missing_actresses()
            second = await missing.list_missing_actresses()
            bypassed = await missing.list_missing_actresses(cache_control="0")

        self.assertEqual(summaries.call_count, 2)
        self.assertEqual(first["data"][0]["actress_id"], 1)
        self.assertNotIn("missing_videos_json", first["data"][0])
        self.assertEqual(second["data"][0]["actress_id"], 1)
        self.assertEqual(bypassed["data"][0]["actress_id"], 2)


class MissingSummaryDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_list_missing_summary_index_omits_large_video_json(self):
        from database import inventory

        inventory.save_missing_summary(
            101,
            "Actor",
            120,
            80,
            '[{"content_id":"MIAA-784","title":"large"}]' * 1000,
        )

        rows = inventory.list_missing_summary_index()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actress_id"], 101)
        self.assertEqual(rows[0]["missing_count"], 80)
        self.assertNotIn("missing_videos_json", rows[0])


if __name__ == "__main__":
    unittest.main()
