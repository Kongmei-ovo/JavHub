from __future__ import annotations

import unittest

from test_support.postgres import TempPostgresMixin


class JobModelTest(TempPostgresMixin, unittest.TestCase):
    def test_create_update_progress_and_cancel_job_lifecycle(self):
        from database.job import (
            cancel_job,
            create_job,
            get_job,
            update_job,
            update_job_progress,
        )

        job_id = create_job("inventory", label="Collect library", trace_id="abc12345")

        created = get_job(job_id)
        self.assertIsNotNone(created)
        self.assertEqual(created["kind"], "inventory")
        self.assertEqual(created["label"], "Collect library")
        self.assertEqual(created["status"], "queued")
        self.assertEqual(created["progress"], 0)
        self.assertEqual(created["trace_id"], "abc12345")
        self.assertIsNone(created["started_at"])

        update_job(job_id, status="running")
        update_job_progress(job_id, 47)
        update_job(
            job_id,
            status="failed",
            error_msg="boom",
            result={"processed": 3, "failed": 1},
        )

        failed = get_job(job_id)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["progress"], 47)
        self.assertEqual(failed["error_msg"], "boom")
        self.assertEqual(failed["result"], {"processed": 3, "failed": 1})
        self.assertIsNotNone(failed["started_at"])
        self.assertIsNotNone(failed["finished_at"])

        canceled_id = create_job("subscription", label="Nightly")
        canceled = cancel_job(canceled_id)
        self.assertTrue(canceled)
        self.assertEqual(get_job(canceled_id)["status"], "canceled")
        self.assertIsNotNone(get_job(canceled_id)["finished_at"])

    def test_list_jobs_filters_by_kind_status_and_since(self):
        from database import get_db
        from database.job import create_job, list_jobs, update_job

        old_id = create_job("inventory", label="old")
        subscription_id = create_job("subscription", label="fresh")
        failed_id = create_job("subscription", label="failed")
        update_job(subscription_id, status="running")
        update_job(failed_id, status="failed")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET created_at = CURRENT_TIMESTAMP - INTERVAL '2 days'
                WHERE id = ?
                """,
                (old_id,),
            )

        subscription_jobs = list_jobs(kind="subscription")
        self.assertEqual([job["id"] for job in subscription_jobs], [failed_id, subscription_id])

        running_jobs = list_jobs(status="running")
        self.assertEqual([job["id"] for job in running_jobs], [subscription_id])

        recent_jobs = list_jobs(since="1 day", limit=10)
        self.assertEqual([job["id"] for job in recent_jobs], [failed_id, subscription_id])

    def test_worker_submit_creates_job_row_and_exposes_current_job_id(self):
        from database.job import get_current_job_id, list_jobs
        from scheduler.worker_loop import submit

        async def read_current_job_id():
            return get_current_job_id()

        future = submit(read_current_job_id(), kind="test", label="worker smoke")
        job_id = future.result(timeout=3)

        jobs = list_jobs(kind="test")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], job_id)
        self.assertEqual(jobs[0]["label"], "worker smoke")
        self.assertEqual(jobs[0]["status"], "completed")
        self.assertEqual(jobs[0]["progress"], 100)
        self.assertEqual(jobs[0]["result"], {"value": job_id})


if __name__ == "__main__":
    unittest.main()
