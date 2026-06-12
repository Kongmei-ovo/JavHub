from __future__ import annotations

import unittest

from test_support.postgres import TempPostgresMixin


class MovieResourcesDatabaseTests(TempPostgresMixin, unittest.TestCase):
    def test_upsert_is_idempotent_by_provider_and_remote_file_id(self):
        from database import get_movie_resource, upsert_movie_resource

        resource_id, created = upsert_movie_resource(
            movie_id="dmm:abc123",
            provider="open115",
            remote_file_id="file-1",
            parent_id="folder-1",
            pick_code="pick-1",
            name="movie.mkv",
            extension="mkv",
            size=100,
            duration=7200,
            status="ready",
            is_default=True,
            download_task_id=7,
        )
        same_id, created_again = upsert_movie_resource(
            movie_id="dmm:abc123",
            provider="open115",
            remote_file_id="file-1",
            parent_id="folder-2",
            pick_code="pick-2",
            name="movie-renamed.mkv",
            extension=".MKV",
            size=200,
            duration=7300,
            status="ready",
            is_default=True,
            download_task_id=7,
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(resource_id, same_id)
        row = get_movie_resource(resource_id)
        self.assertEqual(row["parent_id"], "folder-2")
        self.assertEqual(row["pick_code"], "pick-2")
        self.assertEqual(row["extension"], "mkv")
        self.assertEqual(row["size"], 200)

    def test_setting_default_clears_previous_default_for_same_movie(self):
        from database import (
            list_movie_resources,
            set_default_movie_resource,
            upsert_movie_resource,
        )

        first_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-1",
            name="large.mp4", size=1000, status="ready", is_default=True,
        )
        second_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-2",
            name="small.mp4", size=100, status="ready",
        )

        self.assertTrue(set_default_movie_resource("movie-1", second_id))
        rows = list_movie_resources("movie-1")

        self.assertEqual([row["id"] for row in rows if row["is_default"]], [second_id])
        self.assertFalse(next(row for row in rows if row["id"] == first_id)["is_default"])

    def test_default_must_be_ready_video_owned_by_movie(self):
        from database import set_default_movie_resource, upsert_movie_resource

        subtitle_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="sub-1",
            name="movie.srt", resource_type="subtitle", status="ready",
        )
        missing_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-1",
            name="movie.mp4", resource_type="video", status="missing",
        )
        other_id, _ = upsert_movie_resource(
            movie_id="movie-2", provider="open115", remote_file_id="file-2",
            name="other.mp4", status="ready",
        )

        self.assertFalse(set_default_movie_resource("movie-1", subtitle_id))
        self.assertFalse(set_default_movie_resource("movie-1", missing_id))
        self.assertFalse(set_default_movie_resource("movie-1", other_id))

    def test_delete_default_promotes_largest_ready_video(self):
        from database import (
            delete_movie_resource,
            list_movie_resources,
            upsert_movie_resource,
        )

        default_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-1",
            name="default.mp4", size=500, status="ready", is_default=True,
        )
        largest_id, _ = upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-2",
            name="largest.mkv", size=900, status="ready",
        )
        upsert_movie_resource(
            movie_id="movie-1", provider="open115", remote_file_id="file-3",
            name="failed.mp4", size=2000, status="failed",
        )

        self.assertTrue(delete_movie_resource("movie-1", default_id))
        rows = list_movie_resources("movie-1")

        self.assertEqual([row["id"] for row in rows if row["is_default"]], [largest_id])

    def test_transient_urls_are_not_columns(self):
        from database.base import get_db

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = 'movie_resources'
                """
            )
            columns = {row["column_name"] for row in cursor.fetchall()}

        self.assertNotIn("downurl", columns)
        self.assertNotIn("stream_url", columns)
        self.assertNotIn("m3u8_url", columns)
        self.assertIn("pick_code", columns)


if __name__ == "__main__":
    unittest.main()
