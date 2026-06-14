from __future__ import annotations

import unittest

import psycopg2

from test_support.postgres import TempPostgresMixin


class AcquisitionSessionTests(TempPostgresMixin, unittest.TestCase):
    def test_single_active_session_per_movie(self):
        from database import (
            create_acquisition_session,
            finish_acquisition_session,
            get_active_session_for_movie,
            get_or_create_active_session,
        )

        s1 = create_acquisition_session(movie_id="ABC-1", trigger="user")
        self.assertEqual(s1["status"], "searching")
        self.assertEqual(s1["movie_id"], "ABC-1")
        self.assertEqual(s1["trigger"], "user")

        # A second trigger for the same movie reuses the active session.
        s_again = get_or_create_active_session(movie_id="ABC-1", trigger="subscription")
        self.assertEqual(s_again["id"], s1["id"])

        active = get_active_session_for_movie("ABC-1")
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], s1["id"])

        # Once terminal there is no active session, and a fresh one can open.
        finish_acquisition_session(s1["id"], status="ready")
        self.assertIsNone(get_active_session_for_movie("ABC-1"))

        s2 = get_or_create_active_session(movie_id="ABC-1", trigger="user")
        self.assertNotEqual(s2["id"], s1["id"])

    def test_partial_unique_index_rejects_second_active_insert(self):
        from database import create_acquisition_session

        create_acquisition_session(movie_id="DUP-1", trigger="user")
        with self.assertRaises(psycopg2.IntegrityError):
            create_acquisition_session(movie_id="DUP-1", trigger="user")

    def test_update_pointers_and_terminal_fields(self):
        from database import (
            create_acquisition_session,
            finish_acquisition_session,
            get_acquisition_session,
            mark_session_detached,
            update_acquisition_session,
        )

        s = create_acquisition_session(movie_id="UPD-1", trigger="user")
        update_acquisition_session(
            s["id"],
            status="submitted",
            download_task_id=42,
            selected_info_hash="deadbeef",
        )
        row = get_acquisition_session(s["id"])
        self.assertEqual(row["status"], "submitted")
        self.assertEqual(row["download_task_id"], 42)
        self.assertEqual(row["selected_info_hash"], "deadbeef")
        self.assertEqual(row["detached"], 0)

        # Detaching the waiting page does not end the session.
        mark_session_detached(s["id"])
        row = get_acquisition_session(s["id"])
        self.assertEqual(row["detached"], 1)
        self.assertEqual(row["status"], "submitted")

        finish_acquisition_session(
            s["id"], status="failed", error_code="weak_match", error_msg="no exact code"
        )
        row = get_acquisition_session(s["id"])
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error_code"], "weak_match")
        self.assertEqual(row["error_msg"], "no exact code")

    def test_finish_requires_terminal_status(self):
        from database import create_acquisition_session, finish_acquisition_session

        s = create_acquisition_session(movie_id="BAD-1", trigger="user")
        with self.assertRaises(ValueError):
            finish_acquisition_session(s["id"], status="downloading")


if __name__ == "__main__":
    unittest.main()
