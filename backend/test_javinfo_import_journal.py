from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class JavInfoImportJournalTest(unittest.IsolatedAsyncioTestCase):
    def _settings(self, password: str = "super-secret") -> dict:
        return {
            "host": "localhost",
            "port": 5432,
            "database": "r18",
            "maintenance_database": "postgres",
            "user": "javhub",
            "password": password,
            "max_parallel_jobs": 2,
            "keep_previous_databases": 1,
        }

    def test_manager_loads_prior_jobs_from_redacted_json_journal(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            first = JavInfoImportManager(storage_dir=storage_dir)
            created = first.create_job(
                self._settings(),
                filename="r18.dump",
                file_size=123,
                confirm_replace=True,
            )

            journal_path = storage_dir / "jobs.json"
            self.assertTrue(journal_path.exists())
            journal_text = journal_path.read_text(encoding="utf-8")
            self.assertNotIn("super-secret", journal_text)

            journal = json.loads(journal_text)
            self.assertEqual(journal["jobs"][0]["settings"]["password"], "")
            self.assertEqual(journal["jobs"][0]["filename"], "r18.dump")

            second = JavInfoImportManager(storage_dir=storage_dir)

            self.assertEqual(second.get_job(created["id"])["filename"], "r18.dump")
            self.assertEqual(second.get_job(created["id"])["settings"]["password"], "")
            self.assertEqual(second.list_jobs()[0]["id"], created["id"])

    async def test_upload_progress_updates_json_journal(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            manager = JavInfoImportManager(storage_dir=storage_dir)
            created = manager.create_job(
                self._settings(password=""),
                filename="r18.sql",
                file_size=31,
                confirm_replace=True,
            )

            await manager.save_upload_chunk(created["id"], b"CREATE TABLE movies", offset=0, total_size=31)

            journal = json.loads((storage_dir / "jobs.json").read_text(encoding="utf-8"))
            saved = journal["jobs"][0]
            self.assertEqual(saved["id"], created["id"])
            self.assertEqual(saved["status"], "uploading")
            self.assertEqual(saved["stage"], "uploading")
            self.assertEqual(saved["uploaded_bytes"], 19)
            self.assertEqual(saved["file_size"], 31)

    def test_journal_keeps_optional_staging_and_backup_names(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            manager = JavInfoImportManager(storage_dir=storage_dir)
            created = manager.create_job(
                self._settings(password=""),
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
            )
            manager._jobs[created["id"]]["staging_name"] = "r18_import_1"
            manager._jobs[created["id"]]["backup_name"] = "r18_before_import_20240101010101"

            manager._persist_jobs_journal()

            reloaded = JavInfoImportManager(storage_dir=storage_dir).get_job(created["id"])
            self.assertEqual(reloaded["staging_name"], "r18_import_1")
            self.assertEqual(reloaded["backup_name"], "r18_before_import_20240101010101")
