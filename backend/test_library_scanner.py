from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from services.openlist import FsEntry, OpenListFsError

LIB_CONFIG = {
    "library": {
        "enabled": True,
        "backend": "openlist",
        "root_paths": ["/115/AV"],
        "scan_interval_ms": 0,
    }
}


class FakeFsClient:
    """以 dict 模拟目录树：{"/115/AV": [FsEntry, ...], ...}"""

    def __init__(self, tree: dict[str, list[FsEntry]], fail_paths: set[str] | None = None):
        self.tree = tree
        self.fail_paths = fail_paths or set()
        self.listed: list[str] = []

    async def fs_list(self, path: str):
        self.listed.append(path)
        if path in self.fail_paths:
            raise OpenListFsError(path, "storage offline")
        return self.tree.get(path, [])


def _file(path: str, name: str, size: int = 10) -> FsEntry:
    return FsEntry(name=name, path=f"{path}/{name}", is_dir=False, size=size, modified="2026-01-01")


def _dir(path: str, name: str) -> FsEntry:
    return FsEntry(name=name, path=f"{path}/{name}", is_dir=True, size=0, modified="")


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.upserts: list[dict] = []
        self.deleted_calls: list[tuple] = []
        self.scan_runs: list[dict] = []

        def fake_upsert(**kwargs):
            self.upserts.append(kwargs)
            return len(self.upserts), True

        def fake_mark_deleted(backend, seen_paths, prefix=None):
            self.deleted_calls.append((backend, set(seen_paths), prefix))
            return 0

        def fake_create_run(mode, root_path=None):
            self.scan_runs.append({"mode": mode, "root_path": root_path})
            return 1

        self.patches = [
            patch("services.library_scanner.upsert_library_file", side_effect=fake_upsert),
            patch("services.library_scanner.mark_files_deleted", side_effect=fake_mark_deleted),
            patch("services.library_scanner.create_scan_run", side_effect=fake_create_run),
            patch("services.library_scanner.update_scan_run"),
            patch("services.library_scanner.config._config", LIB_CONFIG),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def _scan(self, tree, mode="full", paths=None, fail_paths=None):
        from services.library_scanner import LibraryScanner

        scanner = LibraryScanner(client=FakeFsClient(tree, fail_paths))
        return asyncio.run(scanner.scan(mode=mode, paths=paths))

    def test_extracts_code_from_filename(self):
        tree = {"/115/AV": [_file("/115/AV", "ABC-123.mp4"), _file("/115/AV", "notes.txt")]}
        result = self._scan(tree)
        self.assertEqual(result["seen"], 1)  # txt 被扩展名过滤
        self.assertEqual(result["matched"], 1)
        self.assertEqual(self.upserts[0]["content_id"], "ABC-123")
        self.assertEqual(self.upserts[0]["match_status"], "matched")

    def test_falls_back_to_parent_dir_code(self):
        tree = {
            "/115/AV": [_dir("/115/AV", "DEF-456")],
            "/115/AV/DEF-456": [_file("/115/AV/DEF-456", "movie.mp4")],
        }
        self._scan(tree)
        self.assertEqual(self.upserts[0]["content_id"], "DEF-456")

    def test_unmatched_when_no_code_anywhere(self):
        tree = {"/115/AV": [_file("/115/AV", "holiday video.mp4")]}
        result = self._scan(tree)
        self.assertEqual(result["matched"], 0)
        self.assertIsNone(self.upserts[0]["content_id"])
        self.assertEqual(self.upserts[0]["match_status"], "unmatched")

    def test_full_scan_marks_missing_files_deleted(self):
        tree = {"/115/AV": [_file("/115/AV", "ABC-123.mp4")]}
        self._scan(tree, mode="full")
        self.assertEqual(len(self.deleted_calls), 1)
        backend, seen, prefix = self.deleted_calls[0]
        self.assertEqual(backend, "openlist")
        self.assertEqual(seen, {"/115/AV/ABC-123.mp4"})
        self.assertIsNone(prefix)

    def test_incremental_scan_scopes_deletion_to_prefix(self):
        tree = {"/115/AV/new": [_file("/115/AV/new", "GHI-789.mp4")]}
        self._scan(tree, mode="incremental", paths=["/115/AV/new"])
        self.assertEqual(self.deleted_calls[0][2], "/115/AV/new")

    def test_single_dir_failure_does_not_abort_scan(self):
        tree = {
            "/115/AV": [_dir("/115/AV", "bad"), _dir("/115/AV", "good")],
            "/115/AV/good": [_file("/115/AV/good", "JKL-321.mp4")],
        }
        result = self._scan(tree, fail_paths={"/115/AV/bad"})
        self.assertEqual(result["seen"], 1)
        self.assertEqual(result["errors"], 1)


class IncrementalDebounceTests(unittest.TestCase):
    def test_debounce_suppresses_repeat_triggers(self):
        import services.library_scanner as scanner_mod

        calls = []

        async def fake_run_scan(mode, paths):
            calls.append((mode, paths))
            return {}

        with patch("services.library_scanner.config._config", LIB_CONFIG), \
             patch("services.library_scanner.run_scan", side_effect=fake_run_scan), \
             patch.dict(scanner_mod._recent_incremental, {}, clear=True):
            first = asyncio.run(scanner_mod.trigger_incremental_scan("/115/AV/x"))
            second = asyncio.run(scanner_mod.trigger_incremental_scan("/115/AV/x"))

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
