"""library_files / library_scan_runs / playback_progress CRUD（需要 PostgreSQL，CI 运行）。"""
from __future__ import annotations

import unittest

from test_support.postgres import TempPostgresMixin


class LibraryFilesCrudTests(TempPostgresMixin, unittest.TestCase):
    def test_upsert_insert_then_update(self):
        from database import get_library_file, upsert_library_file

        file_id, created = upsert_library_file(
            backend="openlist", path="/115/AV/ABC-123.mp4", name="ABC-123.mp4",
            size=100, content_id="ABC-123", match_status="matched",
        )
        self.assertTrue(created)
        same_id, created_again = upsert_library_file(
            backend="openlist", path="/115/AV/ABC-123.mp4", name="ABC-123.mp4",
            size=200, content_id="ABC-123", match_status="matched",
        )
        self.assertEqual(file_id, same_id)
        self.assertFalse(created_again)
        row = get_library_file(file_id)
        self.assertEqual(row["size"], 200)

    def test_manual_match_not_overwritten_by_scan(self):
        from database import get_library_file, set_file_match, upsert_library_file

        file_id, _ = upsert_library_file(
            backend="openlist", path="/115/AV/x.mp4", name="x.mp4", match_status="unmatched",
        )
        set_file_match(file_id, "XYZ-999", status="manual")
        upsert_library_file(
            backend="openlist", path="/115/AV/x.mp4", name="x.mp4",
            content_id=None, match_status="unmatched",
        )
        row = get_library_file(file_id)
        self.assertEqual(row["content_id"], "XYZ-999")
        self.assertEqual(row["match_status"], "manual")

    def test_mark_files_deleted_and_revive(self):
        from database import get_library_file, mark_files_deleted, upsert_library_file

        keep_id, _ = upsert_library_file(
            backend="openlist", path="/115/AV/keep.mp4", name="keep.mp4",
        )
        gone_id, _ = upsert_library_file(
            backend="openlist", path="/115/AV/gone.mp4", name="gone.mp4",
        )
        removed = mark_files_deleted("openlist", {"/115/AV/keep.mp4"})
        self.assertEqual(removed, 1)
        self.assertIsNone(get_library_file(keep_id)["deleted_at"])
        self.assertIsNotNone(get_library_file(gone_id)["deleted_at"])

        # 重新出现 → 复活
        upsert_library_file(backend="openlist", path="/115/AV/gone.mp4", name="gone.mp4")
        self.assertIsNone(get_library_file(gone_id)["deleted_at"])

    def test_mark_files_deleted_respects_prefix(self):
        from database import get_library_file, mark_files_deleted, upsert_library_file

        in_scope, _ = upsert_library_file(
            backend="openlist", path="/115/AV/new/a.mp4", name="a.mp4",
        )
        out_of_scope, _ = upsert_library_file(
            backend="openlist", path="/115/AV/old/b.mp4", name="b.mp4",
        )
        mark_files_deleted("openlist", set(), prefix="/115/AV/new")
        self.assertIsNotNone(get_library_file(in_scope)["deleted_at"])
        self.assertIsNone(get_library_file(out_of_scope)["deleted_at"])

    def test_get_by_content_id_orders_by_size_and_excludes_ignored(self):
        from database import get_library_files_by_content_id, ignore_file, upsert_library_file

        upsert_library_file(
            backend="openlist", path="/115/AV/s.mp4", name="s.mp4", size=10,
            content_id="ABC-123", match_status="matched",
        )
        upsert_library_file(
            backend="openlist", path="/115/AV/l.mp4", name="l.mp4", size=999,
            content_id="ABC-123", match_status="matched",
        )
        ignored_id, _ = upsert_library_file(
            backend="openlist", path="/115/AV/i.mp4", name="i.mp4", size=5000,
            content_id="ABC-123", match_status="matched",
        )
        ignore_file(ignored_id)
        files = get_library_files_by_content_id("ABC-123")
        self.assertEqual([f["name"] for f in files], ["l.mp4", "s.mp4"])

    def test_summary_counts(self):
        from database import ignore_file, library_summary, upsert_library_file

        upsert_library_file(
            backend="openlist", path="/115/AV/a.mp4", name="a.mp4",
            content_id="AAA-111", match_status="matched",
        )
        upsert_library_file(
            backend="openlist", path="/115/AV/b.mp4", name="b.mp4", match_status="unmatched",
        )
        bad_id, _ = upsert_library_file(
            backend="openlist", path="/115/AV/c.mp4", name="c.mp4", match_status="unmatched",
        )
        ignore_file(bad_id)
        summary = library_summary()
        self.assertEqual(summary["total_files"], 3)
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["unmatched"], 1)
        self.assertEqual(summary["ignored"], 1)
        self.assertEqual(summary["distinct_titles"], 1)

    def test_scan_run_lifecycle(self):
        from database import create_scan_run, get_latest_scan_run, is_scan_running, update_scan_run

        run_id = create_scan_run("full", root_path="/115/AV")
        self.assertTrue(is_scan_running())
        update_scan_run(run_id, status="done", files_seen=5, files_matched=4)
        self.assertFalse(is_scan_running())
        latest = get_latest_scan_run()
        self.assertEqual(latest["id"], run_id)
        self.assertEqual(latest["files_seen"], 5)
        self.assertIsNotNone(latest["finished_at"])


class PlaybackProgressTests(TempPostgresMixin, unittest.TestCase):
    def test_save_progress_upsert_idempotent(self):
        from database import get_progress, save_progress

        save_progress("ABC-123", "library", 120.5, 7200)
        save_progress("ABC-123", "library", 300.0, 7200)
        row = get_progress("ABC-123", source="library")
        self.assertAlmostEqual(row["position_seconds"], 300.0)
        self.assertEqual(row["completed"], 0)

    def test_completed_threshold(self):
        from database import get_progress, save_progress

        save_progress("ABC-123", "library", 6900, 7200)  # 95.8%
        self.assertEqual(get_progress("ABC-123", "library")["completed"], 1)
        save_progress("DEF-456", "library", 6700, 7200)  # 93%
        self.assertEqual(get_progress("DEF-456", "library")["completed"], 0)

    def test_continue_watching_filters_and_dedupes(self):
        from database import list_continue_watching, save_progress

        save_progress("AAA-111", "library", 600, 7200)   # 入选
        save_progress("BBB-222", "library", 10, 7200)    # position < 30s 排除
        save_progress("CCC-333", "library", 7100, 7200)  # completed 排除
        save_progress("AAA-111", "online", 700, 7200)    # 同番号去重
        items = list_continue_watching(limit=10)
        self.assertEqual([i["content_id"] for i in items], ["AAA-111"])


if __name__ == "__main__":
    unittest.main()
