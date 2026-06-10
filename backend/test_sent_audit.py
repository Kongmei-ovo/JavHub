"""Tests for the sent-candidate audit loop (P0-1.2)."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class SentAuditTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_promotes_to_completed_when_downloader_done_and_emby_has_it(self):
        from database import (
            add_missing_video,
            create_download_task,
            get_download_candidate,
            get_missing_video,
            set_download_candidate_status,
            update_task_status,
            upsert_download_candidate,
            upsert_inventory_actor,
        )
        from services.sent_audit import audit_sent_candidates

        upsert_inventory_actor(1, "Actor")
        add_missing_video("SIVR-438", 1, "Title", "2026-01-01", "")
        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        task_id = create_download_task("SIVR-438", "Title", "magnet:?xt", "/tmp")
        update_task_status(task_id, "completed")
        set_download_candidate_status(candidate["id"], "sent", download_task_id=task_id)

        with patch("services.sent_audit.get_emby_client") as get_emby:
            emby = AsyncMock()
            emby.check_exists.return_value = True
            get_emby.return_value = emby
            result = await audit_sent_candidates()

        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed"], 0)
        refreshed = get_download_candidate(candidate["id"])
        self.assertEqual(refreshed["status"], "completed")
        self.assertIsNone(get_missing_video("SIVR-438"))

    async def test_reverts_to_failed_when_download_task_failed(self):
        from database import (
            create_download_task,
            get_download_candidate,
            set_download_candidate_status,
            update_task_status,
            upsert_download_candidate,
        )
        from services.sent_audit import audit_sent_candidates

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        task_id = create_download_task("SIVR-438", "Title", "magnet:?xt", "/tmp")
        update_task_status(task_id, "failed", "openlist timeout")
        set_download_candidate_status(candidate["id"], "sent", download_task_id=task_id)

        with patch("services.sent_audit.get_emby_client") as get_emby:
            get_emby.return_value = AsyncMock()
            result = await audit_sent_candidates()

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["completed"], 0)
        refreshed = get_download_candidate(candidate["id"])
        self.assertEqual(refreshed["status"], "failed")

    async def test_emby_failure_does_not_demote_candidates(self):
        from database import (
            create_download_task,
            get_download_candidate,
            set_download_candidate_status,
            update_task_status,
            upsert_download_candidate,
        )
        from modules.emby_client import EmbyUnavailableError
        from services.sent_audit import audit_sent_candidates

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        task_id = create_download_task("SIVR-438", "Title", "magnet:?xt", "/tmp")
        update_task_status(task_id, "completed")
        set_download_candidate_status(candidate["id"], "sent", download_task_id=task_id)

        with patch("services.sent_audit.get_emby_client") as get_emby:
            emby = AsyncMock()
            emby.check_exists.side_effect = EmbyUnavailableError("down")
            get_emby.return_value = emby
            result = await audit_sent_candidates()

        self.assertGreaterEqual(result["emby_unavailable"], 1)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "sent")

    async def test_pending_when_downloader_still_in_flight(self):
        from database import (
            create_download_task,
            get_download_candidate,
            set_download_candidate_status,
            update_task_status,
            upsert_download_candidate,
        )
        from services.sent_audit import audit_sent_candidates

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        task_id = create_download_task("SIVR-438", "Title", "magnet:?xt", "/tmp")
        update_task_status(task_id, "downloading")
        set_download_candidate_status(candidate["id"], "sent", download_task_id=task_id)

        with patch("services.sent_audit.get_emby_client") as get_emby:
            get_emby.return_value = AsyncMock()
            result = await audit_sent_candidates()

        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "sent")


if __name__ == "__main__":
    unittest.main()
