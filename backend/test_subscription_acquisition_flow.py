from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


def _sub():
    return {
        "id": 1,
        "scope": "actress",
        "actress_id": 123,
        "actress_name": "Actor",
        "target_id": 123,
        "target_label": "Actor",
        "last_seen_codes": [],
    }


def _pipeline(videos):
    pipeline = AsyncMock()
    pipeline.fetch_actress_videos = AsyncMock(return_value=videos)
    return pipeline


class SubscriptionAcquisitionFlowTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def _run(self, videos, start):
        from services import subscription

        with patch.object(subscription, "start_acquisition", new=start), patch(
            "services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()
        ), patch.object(
            subscription, "_subscription_auto_acquire_enabled", return_value=True
        ):
            return await subscription._run_subscription_check(_sub(), _pipeline(videos))

    async def test_first_check_only_establishes_baseline_no_downloads(self):
        from database import get_baseline_at

        start = AsyncMock()
        videos = [{"content_id": "OLD-1", "dvd_id": "OLD-1", "title": "t"}]
        result = await self._run(videos, start)

        self.assertTrue(result["baseline_established"])
        self.assertEqual(start.await_count, 0)  # baseline-only: download nothing
        self.assertIsNotNone(get_baseline_at(1))

    async def test_new_dated_code_triggers_acquisition_dateless_and_old_go_manual(self):
        from database import establish_baseline, is_in_baseline

        establish_baseline(1, ["OLD-1"])  # baseline_at = now
        videos = [
            {"content_id": "OLD-1", "dvd_id": "OLD-1"},
            {"content_id": "FUTURE-1", "dvd_id": "FUTURE-1", "title": "f", "release_date": "2999-01-01"},
            {"content_id": "PAST-1", "dvd_id": "PAST-1", "title": "p", "release_date": "1999-01-01"},
            {"content_id": "NODATE-1", "dvd_id": "NODATE-1", "title": "n"},
        ]
        start = AsyncMock()
        result = await self._run(videos, start)

        start.assert_awaited_once()
        self.assertEqual(start.await_args.args[0], "FUTURE-1")  # only the fresh release auto-fires
        self.assertEqual({c["content_id"] for c in result["candidates"]}, {"PAST-1", "NODATE-1"})
        # all newly seen codes fold into the baseline so they never re-fire
        for code in ("FUTURE-1", "PAST-1", "NODATE-1"):
            self.assertTrue(is_in_baseline(1, code))

    async def test_ready_resource_and_active_session_skip_acquisition(self):
        from database import (
            create_acquisition_session,
            establish_baseline,
            upsert_movie_resource,
        )

        establish_baseline(1, ["OLD-1"])
        upsert_movie_resource(
            movie_id="HAVE-1", provider="open115", remote_file_id="v",
            name="HAVE-1.mp4", status="ready", is_default=True,
        )
        create_acquisition_session(movie_id="BUSY-1", trigger="user")
        videos = [
            {"content_id": "HAVE-1", "dvd_id": "HAVE-1", "release_date": "2999-01-01"},
            {"content_id": "BUSY-1", "dvd_id": "BUSY-1", "release_date": "2999-01-01"},
        ]
        start = AsyncMock()
        result = await self._run(videos, start)

        self.assertEqual(start.await_count, 0)  # neither re-spends an offline slot
        self.assertEqual(result["in_library"], 1)  # HAVE-1 already ready
        self.assertEqual(result["existing"], 1)  # BUSY-1 already being acquired

    async def test_disabled_auto_download_keeps_fresh_release_as_candidate(self):
        from database import establish_baseline
        from services import subscription

        establish_baseline(1, ["OLD-1"])
        start = AsyncMock()
        videos = [{"content_id": "FUTURE-1", "dvd_id": "FUTURE-1", "release_date": "2999-01-01"}]
        with patch.object(subscription, "start_acquisition", new=start), patch(
            "services.supplement_autopilot.ensure_actress_supplement", new=AsyncMock()
        ), patch.object(subscription, "_subscription_auto_acquire_enabled", return_value=False):
            result = await subscription._run_subscription_check(_sub(), _pipeline(videos))

        start.assert_not_awaited()
        self.assertEqual([candidate["content_id"] for candidate in result["candidates"]], ["FUTURE-1"])
        self.assertEqual(result["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
