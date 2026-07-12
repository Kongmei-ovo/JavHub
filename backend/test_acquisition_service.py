from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


def _result(best_title: str, magnet: str = "magnet:?xt=urn:btih:abc123"):
    best = {"title": best_title, "magnet": magnet, "source": "javdb"}
    return {
        "best": best,
        "candidates": [{"item": best, "score": {"total": 1}}],
        "alternatives": [{"magnet": magnet, "source": "javdb", "title": best_title, "score": {"total": 1}}],
    }


class AcquisitionServiceTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_existing_ready_resource_short_circuits(self):
        from database.movie_resource import upsert_movie_resource
        from database import get_active_session_for_movie
        from services import acquisition

        upsert_movie_resource(
            movie_id="HAVE-1", provider="open115", remote_file_id="v1",
            name="HAVE-1.mp4", status="ready", is_default=True,
        )

        res = await acquisition.start_acquisition("HAVE-1", auto=True)

        self.assertEqual(res["status"], "ready")
        self.assertIsNone(res["session"])
        self.assertTrue(res["resources"])  # the ready resource is surfaced
        self.assertIsNone(get_active_session_for_movie("HAVE-1"))  # no session created

    async def test_repeated_clicks_reuse_session_no_double_offline(self):
        from database import get_download_candidate
        from services import acquisition

        submit = AsyncMock(return_value=777)
        with patch.object(acquisition, "find_best_magnet", new=AsyncMock(return_value=_result("NEW-1 中文字幕 1080p"))), \
             patch.object(acquisition.downloader_service, "create_download_task", new=submit):
            r1 = await acquisition.start_acquisition("NEW-1", auto=True)
            r2 = await acquisition.start_acquisition("NEW-1", auto=True)

        self.assertEqual(r1["session"]["id"], r2["session"]["id"])
        self.assertEqual(r1["session"]["status"], "downloading")
        self.assertEqual(r1["session"]["download_task_id"], 777)
        self.assertEqual(submit.await_count, 1)  # not re-submitted on the second click
        candidate = get_download_candidate(r1["session"]["candidate_id"])
        self.assertEqual(candidate["status"], "sent")
        self.assertEqual(candidate["download_task_id"], 777)

    async def test_weak_match_does_not_auto_submit(self):
        from services import acquisition

        submit = AsyncMock(return_value=1)
        with patch.object(acquisition, "find_best_magnet", new=AsyncMock(return_value=_result("OTHER-9 1080p"))), \
             patch.object(acquisition.downloader_service, "create_download_task", new=submit):
            r = await acquisition.start_acquisition("FUZZY-1", auto=True)

        self.assertEqual(r["session"]["status"], "options_ready")
        self.assertIsNone(r["session"]["download_task_id"])
        self.assertEqual(submit.await_count, 0)  # weak match waits for a human
        self.assertTrue(r["options"])  # options are still offered for manual pick

    async def test_stop_waiting_detaches_without_cancelling(self):
        from database.acquisition_session import TERMINAL_STATUSES
        from services import acquisition

        submit = AsyncMock(return_value=42)
        with patch.object(acquisition, "find_best_magnet", new=AsyncMock(return_value=_result("KEEP-1 1080p"))), \
             patch.object(acquisition.downloader_service, "create_download_task", new=submit):
            started = await acquisition.start_acquisition("KEEP-1", auto=True)
            snap = acquisition.stop_waiting(started["session"]["id"])

        self.assertEqual(snap["session"]["detached"], 1)
        self.assertNotIn(snap["session"]["status"], TERMINAL_STATUSES)  # still running in the background


if __name__ == "__main__":
    unittest.main()
