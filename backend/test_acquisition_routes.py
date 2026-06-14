from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.client import create_router_test_client
from test_support.postgres import TempPostgresMixin


def _search_result(title: str, magnet: str = "magnet:?xt=urn:btih:rt1"):
    best = {"title": title, "magnet": magnet, "source": "javdb"}
    return {
        "best": best,
        "candidates": [{"item": best, "score": {"total": 1}}],
        "alternatives": [{"magnet": magnet, "source": "javdb", "title": title, "score": {"total": 1}}],
    }


class AcquisitionRoutesTests(TempPostgresMixin, unittest.TestCase):
    def _client(self):
        from routers.acquisitions import router

        return create_router_test_client(router)

    def test_start_snapshot_then_stop_waiting_keeps_session_active(self):
        from services import acquisition

        submit = AsyncMock(return_value=555)
        with patch.object(acquisition, "find_best_magnet", new=AsyncMock(return_value=_search_result("RT-1 中文字幕 1080p"))), \
             patch.object(acquisition.downloader_service, "create_download_task", new=submit):
            client = self._client()

            started = client.post("/api/v1/movies/RT-1/acquisitions", json={"auto": True})
            self.assertEqual(started.status_code, 200)
            session_id = started.json()["session"]["id"]
            self.assertEqual(started.json()["session"]["status"], "downloading")
            self.assertEqual(started.json()["session"]["download_task_id"], 555)

            snap = client.get(f"/api/v1/acquisitions/{session_id}")
            self.assertEqual(snap.status_code, 200)
            self.assertEqual(snap.json()["session"]["id"], session_id)

            stopped = client.post(f"/api/v1/acquisitions/{session_id}/stop-waiting")
            self.assertEqual(stopped.status_code, 200)
            self.assertEqual(stopped.json()["session"]["detached"], 1)
            # Closing the waiting page must NOT cancel: session is still active and
            # the offline task was never asked to cancel (submit called exactly once).
            self.assertNotIn(stopped.json()["session"]["status"], ("ready", "failed"))

        self.assertEqual(submit.await_count, 1)

    def test_snapshot_missing_session_returns_404(self):
        client = self._client()
        resp = client.get("/api/v1/acquisitions/999999")
        self.assertEqual(resp.status_code, 404)

    def test_start_requires_movie_id(self):
        client = self._client()
        resp = client.post("/api/v1/movies/%20/acquisitions", json={"auto": True})
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
