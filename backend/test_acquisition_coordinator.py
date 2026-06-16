from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from apscheduler.triggers.interval import IntervalTrigger

from test_support.postgres import TempPostgresMixin


class AcquisitionCoordinatorTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    def test_configure_registers_interval_job(self):
        from scheduler import tasks

        self.assertTrue(hasattr(tasks, "configure_acquisition_coordinator_job"))
        try:
            tasks.configure_acquisition_coordinator_job()
            job = tasks.scheduler.get_job("acquisition_coordinator")
            self.assertIsNotNone(job, "acquisition_coordinator interval job should be registered")
            self.assertIsInstance(job.trigger, IntervalTrigger)
        finally:
            try:
                tasks.scheduler.remove_job("acquisition_coordinator")
            except Exception:
                pass

    def test_start_scheduler_wires_the_coordinator(self):
        # start_scheduler should install the coordinator alongside the other jobs.
        import inspect
        from scheduler import tasks

        source = inspect.getsource(tasks.start_scheduler)
        self.assertIn("configure_acquisition_coordinator_job()", source)

    async def test_failed_task_classifies_into_session_error_code(self):
        from database import create_download_task, update_task_status
        from database.acquisition_session import (
            create_acquisition_session,
            get_acquisition_session,
            update_acquisition_session,
        )
        from services.downloader import downloader_service

        task_id = create_download_task(
            "FAIL-1", "FAIL-1", "magnet:?xt=urn:btih:fail", "",
            downloader_type="open115", movie_id="FAIL-1",
        )
        update_task_status(task_id, "downloading")
        session = create_acquisition_session(movie_id="FAIL-1", trigger="user")
        update_acquisition_session(session["id"], status="downloading", download_task_id=task_id)

        async def fake_poll(tid):
            update_task_status(tid, "failed", "source request timed out")
            return {"task_id": tid, "status": "failed"}

        with patch.object(downloader_service, "poll_task_status", new=AsyncMock(side_effect=fake_poll)):
            await downloader_service.update_all_task_statuses()

        synced = get_acquisition_session(session["id"])
        self.assertEqual(synced["status"], "failed")
        self.assertEqual(synced["error_code"], "source_timeout")

    async def test_completed_task_marks_session_ready(self):
        from database import create_download_task, update_task_status
        from database.acquisition_session import (
            create_acquisition_session,
            get_acquisition_session,
            update_acquisition_session,
        )
        from services.downloader import downloader_service

        task_id = create_download_task(
            "DONE-1", "DONE-1", "magnet:?xt=urn:btih:done", "",
            downloader_type="open115", movie_id="DONE-1",
        )
        update_task_status(task_id, "finalizing")
        session = create_acquisition_session(movie_id="DONE-1", trigger="user")
        update_acquisition_session(session["id"], status="finalizing", download_task_id=task_id)

        async def fake_poll(tid):
            update_task_status(tid, "completed")
            return {"task_id": tid, "status": "completed"}

        with patch.object(downloader_service, "poll_task_status", new=AsyncMock(side_effect=fake_poll)):
            await downloader_service.update_all_task_statuses()

        synced = get_acquisition_session(session["id"])
        self.assertEqual(synced["status"], "ready")


if __name__ == "__main__":
    unittest.main()
