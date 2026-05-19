from __future__ import annotations

import gzip
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


async def _noop_post_import_migrator(job):
    return None


class JavInfoImportConfigTest(unittest.TestCase):
    def test_import_db_defaults_follow_database_env(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {}

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "postgres",
                "DB_PORT": "15432",
                "DB_USER": "javhub",
                "DB_PASSWORD": "change-me",
                "DB_NAME": "r18",
            },
            clear=False,
        ):
            self.assertEqual(
                cfg.javinfo_import_db,
                {
                    "host": "postgres",
                    "port": 15432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "change-me",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
            )

    def test_import_db_config_overrides_database_env(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {
            "javinfo": {
                "import_db": {
                    "host": "db.example",
                    "port": 25432,
                    "database": "custom_r18",
                    "user": "custom_user",
                    "password": "custom-secret",
                }
            }
        }

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "postgres",
                "DB_PORT": "15432",
                "DB_USER": "javhub",
                "DB_PASSWORD": "change-me",
                "DB_NAME": "r18",
            },
            clear=False,
        ):
            self.assertEqual(cfg.javinfo_import_db["host"], "db.example")
            self.assertEqual(cfg.javinfo_import_db["port"], 25432)
            self.assertEqual(cfg.javinfo_import_db["database"], "custom_r18")
            self.assertEqual(cfg.javinfo_import_db["user"], "custom_user")
            self.assertEqual(cfg.javinfo_import_db["password"], "custom-secret")

    def test_import_db_env_replaces_legacy_placeholder_values(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {
            "javinfo": {
                "import_db": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "user": "kongmei",
                    "password": "",
                }
            }
        }

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "postgres",
                "DB_PORT": "15432",
                "DB_USER": "javhub",
                "DB_PASSWORD": "change-me",
                "DB_NAME": "r18",
            },
            clear=False,
        ):
            self.assertEqual(cfg.javinfo_import_db["host"], "postgres")
            self.assertEqual(cfg.javinfo_import_db["port"], 15432)
            self.assertEqual(cfg.javinfo_import_db["user"], "javhub")
            self.assertEqual(cfg.javinfo_import_db["password"], "change-me")

    def test_import_db_allows_zero_previous_databases(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {"javinfo": {"import_db": {"keep_previous_databases": 0}}}

        self.assertEqual(cfg.javinfo_import_db["keep_previous_databases"], 0)

    def test_import_db_password_is_sensitive_and_blank_save_preserves_existing(self):
        from config import Config
        from routers.config import _sanitize_config, _strip_blank_sensitive_values

        sanitized = _sanitize_config(
            {
                "javinfo": {
                    "import_db": {
                        "host": "localhost",
                        "password": "secret",
                    }
                }
            }
        )
        self.assertNotIn("password", sanitized["javinfo"]["import_db"])

        cfg = Config.__new__(Config)
        cfg._config = {
            "javinfo": {
                "import_db": {
                    "host": "localhost",
                    "password": "saved-secret",
                }
            }
        }
        with patch("config.Path") as path_mock, patch("config.yaml.dump") as dump_mock:
            fake_path = MagicMock()
            fake_path.__truediv__.return_value = fake_path
            fake_path.parent.parent = fake_path
            path_mock.return_value = fake_path
            with patch("builtins.open", MagicMock()):
                cfg.update(
                    _strip_blank_sensitive_values(
                        {"javinfo": {"import_db": {"database": "r18_new", "password": ""}}}
                    )
                )

        self.assertEqual(cfg._config["javinfo"]["import_db"]["password"], "saved-secret")
        self.assertEqual(cfg._config["javinfo"]["import_db"]["database"], "r18_new")
        dump_mock.assert_called_once()


class JavInfoDumpFormatTest(unittest.TestCase):
    def test_detects_supported_dump_formats(self):
        from services.javinfo_import import detect_dump_format

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom = root / "r18.dump"
            custom.write_bytes(b"PGDMP\x01\x0e")
            sql = root / "r18.sql"
            sql.write_text("CREATE TABLE movies(id integer);\n", encoding="utf-8")
            compressed = root / "r18.sql.gz"
            with gzip.open(compressed, "wb") as fh:
                fh.write(b"CREATE TABLE movies(id integer);\n")

            self.assertEqual(detect_dump_format(custom, "r18.dump").kind, "custom")
            self.assertEqual(detect_dump_format(sql, "r18.sql").kind, "plain_sql")
            self.assertEqual(detect_dump_format(compressed, "r18.sql.gz").kind, "plain_sql_gzip")

    def test_rejects_pg_dumpall_style_plain_sql(self):
        from services.javinfo_import import detect_dump_format

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_db = root / "dump.sql"
            create_db.write_text("CREATE DATABASE r18;\n", encoding="utf-8")
            connect = root / "dump-connect.sql"
            connect.write_text("\\connect r18\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "pg_dumpall"):
                detect_dump_format(create_db, "dump.sql")
            with self.assertRaisesRegex(ValueError, "pg_dumpall"):
                detect_dump_format(connect, "dump-connect.sql")

    def test_plain_sql_detection_reads_only_a_small_sample(self):
        from services.javinfo_import import detect_dump_format

        with tempfile.TemporaryDirectory() as tmp:
            sql = Path(tmp) / "large.sql"
            sql.write_text("CREATE TABLE movies(id integer);\n", encoding="utf-8")

            with patch.object(Path, "read_bytes", side_effect=AssertionError("loaded full file")):
                self.assertEqual(detect_dump_format(sql, "large.sql").kind, "plain_sql")

    def test_rejects_pg_dumpall_style_gzipped_sql(self):
        from services.javinfo_import import detect_dump_format

        with tempfile.TemporaryDirectory() as tmp:
            compressed = Path(tmp) / "dump.sql.gz"
            with gzip.open(compressed, "wb") as fh:
                fh.write(b"\\connect r18\n")

            with self.assertRaisesRegex(ValueError, "pg_dumpall"):
                detect_dump_format(compressed, "dump.sql.gz")


class JavInfoImportServiceSettingsTest(unittest.TestCase):
    def test_normalize_settings_uses_deployable_user_default(self):
        from services.javinfo_import import _normalize_settings

        self.assertEqual(_normalize_settings({})["user"], "javhub")

    def test_connection_command_uses_deployable_user_default(self):
        from services.javinfo_import import build_psql_command

        command = build_psql_command({}, "r18")

        self.assertEqual(command[command.index("--username") + 1], "javhub")


class JavInfoImportManagerTest(unittest.IsolatedAsyncioTestCase):
    async def test_upload_stream_writes_file_and_updates_sha256(self):
        from services.javinfo_import import JavInfoImportManager

        async def chunks():
            yield b"abc"
            yield b"def"

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "kongmei",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=6,
                confirm_replace=True,
            )

            uploaded = await manager.save_upload(job["id"], chunks())

            self.assertEqual(uploaded["uploaded_bytes"], 6)
            self.assertEqual(uploaded["sha256"], hashlib.sha256(b"abcdef").hexdigest())
            self.assertEqual(Path(uploaded["file_path"]).read_bytes(), b"abcdef")
            self.assertEqual(uploaded["status"], "uploaded")

    async def test_chunk_upload_appends_by_offset_and_finalize_starts_restore_ready_state(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            payload = b"CREATE TABLE movies(id integer);\n"
            first_chunk = b"CREATE TABLE movies"
            second_chunk = b"(id integer);\n"
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=len(payload),
                confirm_replace=True,
            )

            first = await manager.save_upload_chunk(job["id"], first_chunk, offset=0, total_size=len(payload))
            second = await manager.save_upload_chunk(job["id"], second_chunk, offset=len(first_chunk), total_size=len(payload))
            finalized = await manager.finalize_upload(job["id"])

            self.assertEqual(first["uploaded_bytes"], len(first_chunk))
            self.assertEqual(second["uploaded_bytes"], len(payload))
            self.assertEqual(finalized["uploaded_bytes"], len(payload))
            self.assertEqual(finalized["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(Path(finalized["file_path"]).read_bytes(), payload)
            self.assertEqual(finalized["status"], "uploaded")

    async def test_chunk_upload_rejects_offset_mismatch_without_overwriting_partial_file(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=31,
                confirm_replace=True,
            )

            await manager.save_upload_chunk(job["id"], b"CREATE TABLE movies", offset=0, total_size=31)

            with self.assertRaisesRegex(ValueError, "offset mismatch"):
                await manager.save_upload_chunk(job["id"], b"bad", offset=0, total_size=31)

            partial_path = Path(manager._jobs[job["id"]]["file_path"]).with_suffix(".sql.part")
            self.assertEqual(partial_path.read_bytes(), b"CREATE TABLE movies")
            self.assertEqual(manager.get_job(job["id"])["uploaded_bytes"], 19)

    async def test_chunk_upload_rejects_canceled_job(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=31,
                confirm_replace=True,
            )

            await manager.cancel_job(job["id"])

            with self.assertRaisesRegex(ValueError, "not accepting uploads"):
                await manager.save_upload_chunk(job["id"], b"CREATE TABLE movies", offset=0, total_size=31)

    async def test_finalize_upload_rejects_incomplete_partial_file(self):
        from services.javinfo_import import JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=31,
                confirm_replace=True,
            )

            await manager.save_upload_chunk(job["id"], b"CREATE TABLE movies", offset=0, total_size=31)

            with self.assertRaisesRegex(ValueError, "incomplete upload"):
                await manager.finalize_upload(job["id"])

    def test_rejects_second_active_job(self):
        from services.javinfo_import import JavInfoImportConflict, JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            manager.create_job(settings, filename="first.dump", file_size=10, confirm_replace=True)

            with self.assertRaises(JavInfoImportConflict):
                manager.create_job(settings, filename="second.dump", file_size=10, confirm_replace=True)

    def test_restore_commands_are_argument_lists_without_shell(self):
        from services.javinfo_import import build_psql_command, build_pg_restore_command

        settings = {
            "host": "localhost",
            "port": 5432,
            "database": "r18",
            "maintenance_database": "postgres",
            "user": "kongmei",
            "password": "secret",
            "max_parallel_jobs": 4,
            "keep_previous_databases": 1,
        }

        restore = build_pg_restore_command(settings, "r18_import_1", Path("/tmp/r18.dump"))
        self.assertIsInstance(restore, list)
        self.assertEqual(restore[0], "pg_restore")
        self.assertIn("--exit-on-error", restore)
        self.assertIn("--jobs=4", restore)
        self.assertNotIn("secret", " ".join(restore))
        self.assertNotIn("|", restore)

        psql = build_psql_command(settings, "r18_import_1", Path("/tmp/r18.sql"))
        self.assertIsInstance(psql, list)
        self.assertEqual(psql[0], "psql")
        self.assertIn("--set=ON_ERROR_STOP=1", psql)
        self.assertNotIn("secret", " ".join(psql))
        self.assertNotIn("|", psql)

    async def test_direct_restore_fallback_resets_target_schema_before_restore(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(
                settings,
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
                confirm_direct_restore=True,
            )
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        self.assertEqual(restored["status"], "completed")
        sql_calls = [" ".join(call) for call in runner.calls if call[0] == "psql"]
        restore_calls = [" ".join(call) for call in runner.calls if call[0] == "pg_restore"]
        self.assertTrue(any("DROP SCHEMA IF EXISTS public CASCADE" in call for call in sql_calls))
        self.assertTrue(restore_calls)

    async def test_direct_restore_requires_explicit_confirmation(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            async def run(self, args, **kwargs):
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=Runner(),
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(
                settings,
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
            )
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        self.assertEqual(restored["status"], "failed")
        self.assertIn("direct restore confirmation is required", restored["error"])

    async def test_restore_runs_post_import_migrations_after_database_import(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                return CommandResult(returncode=0, output="")

        migration_calls = []

        async def run_post_import_migrations(job):
            migration_calls.append((job["id"], job["stage"]))

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=run_post_import_migrations,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(
                settings,
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
                confirm_direct_restore=True,
            )
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        self.assertEqual(restored["status"], "completed")
        self.assertEqual(migration_calls, [(job["id"], "migrating")])
        self.assertTrue(any("JavInfoApi migrations completed" in line for line in restored["logs"]))

    async def test_stream_plain_sql_upload_restores_without_persisting_dump_file(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.stdin_payloads = []

            async def run(self, args, **kwargs):
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                chunks = kwargs.get("stdin_chunks")
                if chunks is not None:
                    payload = b""
                    async for chunk in chunks:
                        payload += chunk
                    self.stdin_payloads.append((args, payload, kwargs.get("gzip_stdin", False)))
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"CREATE TABLE movies"
            yield b"(id integer);\n"

        payload = b"CREATE TABLE movies(id integer);\n"
        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql",
                file_size=len(payload),
                confirm_replace=True,
                confirm_direct_restore=True,
            )

            restored = await manager.restore_upload_stream(job["id"], chunks())

        self.assertEqual(restored["status"], "completed")
        self.assertEqual(restored["uploaded_bytes"], len(payload))
        self.assertEqual(restored["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertFalse(Path(restored["file_path"]).exists())
        self.assertEqual(len(runner.stdin_payloads), 1)
        command, restored_payload, gzip_stdin = runner.stdin_payloads[0]
        self.assertEqual(command[0], "psql")
        self.assertEqual(restored_payload, payload)
        self.assertFalse(gzip_stdin)

    async def test_stream_gzipped_sql_upload_pipes_compressed_body_to_psql_gzip_stdin(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.stdin_payloads = []

            async def run(self, args, **kwargs):
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                chunks = kwargs.get("stdin_chunks")
                if chunks is not None:
                    payload = b""
                    async for chunk in chunks:
                        payload += chunk
                    self.stdin_payloads.append((payload, kwargs.get("gzip_stdin", False)))
                return CommandResult(returncode=0, output="")

        compressed = gzip.compress(b"CREATE TABLE movies(id integer);\n")

        async def chunks():
            yield compressed[:10]
            yield compressed[10:]

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            job = manager.create_job(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                    "max_parallel_jobs": 2,
                    "keep_previous_databases": 1,
                },
                filename="r18.sql.gz",
                file_size=len(compressed),
                confirm_replace=True,
                confirm_direct_restore=True,
            )

            restored = await manager.restore_upload_stream(job["id"], chunks())

        self.assertEqual(restored["status"], "completed")
        self.assertEqual(restored["uploaded_bytes"], len(compressed))
        self.assertEqual(restored["dump_format"], "plain_sql_gzip")
        self.assertFalse(Path(restored["file_path"]).exists())
        self.assertEqual(runner.stdin_payloads, [(compressed, True)])

    async def test_migrating_status_blocks_second_import_job(self):
        from services.javinfo_import import JavInfoImportConflict, JavInfoImportManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(storage_dir=Path(tmp))
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            first = manager.create_job(settings, filename="first.dump", file_size=10, confirm_replace=True)
            manager._jobs[first["id"]]["status"] = "migrating"

            with self.assertRaises(JavInfoImportConflict):
                manager.create_job(settings, filename="second.dump", file_size=10, confirm_replace=True)

    async def test_restore_fails_when_post_import_migrations_fail(self):
        from services.javinfo_import import CommandResult, JavInfoImportError, JavInfoImportManager

        class Runner:
            async def run(self, args, **kwargs):
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                return CommandResult(returncode=0, output="")

        async def fail_migrations(job):
            raise JavInfoImportError("migration failed")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=Runner(),
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=fail_migrations,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(
                settings,
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
                confirm_direct_restore=True,
            )
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        self.assertEqual(restored["status"], "failed")
        self.assertIn("migration failed", restored["error"])

    async def test_restore_failure_after_stopping_service_restarts_javinfo(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and "SELECT rolsuper OR rolcreatedb" in args:
                    return CommandResult(returncode=0, output="f\n")
                if args[0] == "pg_restore":
                    return CommandResult(returncode=1, output="restore failed")
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            helper = Path(tmp) / "services.sh"
            helper.write_text("#!/bin/sh\n", encoding="utf-8")
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp) / "imports",
                command_runner=runner,
                service_helper=helper,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(
                settings,
                filename="r18.dump",
                file_size=20,
                confirm_replace=True,
                confirm_direct_restore=True,
            )
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        service_calls = [call[1:] for call in runner.calls if call[0] == str(helper)]
        self.assertEqual(restored["status"], "failed")
        self.assertIn(["stop", "javinfo"], service_calls)
        self.assertIn(["restart", "javinfo"], service_calls)

    async def test_keep_zero_previous_databases_drops_all_backups(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and any("SELECT datname FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(
                        returncode=0,
                        output="r18_before_import_20240102030405\nr18_before_import_20240101030405\n",
                    )
                return CommandResult(returncode=0, output="")

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(storage_dir=Path(tmp), command_runner=runner)
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 0,
            }

            await manager._cleanup_old_backups(settings, "r18", keep=0)

        sql_calls = [" ".join(call) for call in runner.calls if call[0] == "psql"]
        self.assertTrue(any('DROP DATABASE IF EXISTS "r18_before_import_20240102030405"' in call for call in sql_calls))
        self.assertTrue(any('DROP DATABASE IF EXISTS "r18_before_import_20240101030405"' in call for call in sql_calls))

    async def test_staged_restore_honors_keep_zero_previous_databases(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and any("SELECT rolsuper OR rolcreatedb" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="t\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                if args[0] == "psql" and any("SELECT datname FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(
                        returncode=0,
                        output="r18_before_import_20240102030405\nr18_before_import_20240101030405\n",
                    )
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "kongmei",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 0,
            }
            job = manager.create_job(settings, filename="r18.dump", file_size=20, confirm_replace=True)
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        sql_calls = [" ".join(call) for call in runner.calls if call[0] == "psql"]
        self.assertEqual(restored["status"], "completed")
        self.assertTrue(any('DROP DATABASE IF EXISTS "r18_before_import_20240102030405"' in call for call in sql_calls))
        self.assertTrue(any('DROP DATABASE IF EXISTS "r18_before_import_20240101030405"' in call for call in sql_calls))

    async def test_staged_restore_skips_target_backup_when_target_database_is_missing(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            def __init__(self):
                self.calls = []

            async def run(self, args, **kwargs):
                self.calls.append(args)
                if args[0] == "psql" and any("SELECT rolsuper OR rolcreatedb" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="t\n")
                if args[0] == "psql" and any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="")
                return CommandResult(returncode=0, output="")

        async def chunks():
            yield b"PGDMP fake custom dump"

        with tempfile.TemporaryDirectory() as tmp:
            runner = Runner()
            manager = JavInfoImportManager(
                storage_dir=Path(tmp),
                command_runner=runner,
                service_helper=Path(tmp) / "missing-services.sh",
                post_import_migrator=_noop_post_import_migrator,
            )
            settings = {
                "host": "localhost",
                "port": 5432,
                "database": "r18",
                "maintenance_database": "postgres",
                "user": "javhub",
                "password": "",
                "max_parallel_jobs": 2,
                "keep_previous_databases": 1,
            }
            job = manager.create_job(settings, filename="r18.dump", file_size=20, confirm_replace=True)
            await manager.save_upload(job["id"], chunks())

            restored = await manager.restore_job(job["id"])

        sql_calls = [" ".join(call) for call in runner.calls if call[0] == "psql"]
        self.assertEqual(restored["status"], "completed")
        self.assertFalse(any('ALTER DATABASE "r18" RENAME TO' in call for call in sql_calls))
        self.assertTrue(any('ALTER DATABASE "r18_import_1" RENAME TO "r18"' in call for call in sql_calls))

    async def test_preflight_reports_target_database_existence(self):
        from services.javinfo_import import CommandResult, JavInfoImportManager

        class Runner:
            async def run(self, args, **kwargs):
                if any("SELECT rolsuper OR rolcreatedb" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="t\n")
                if any("SELECT 1 FROM pg_database" in str(arg) for arg in args):
                    return CommandResult(returncode=0, output="1\n")
                return CommandResult(returncode=0, output="")

        with tempfile.TemporaryDirectory() as tmp, patch("services.javinfo_import.shutil.which", return_value="/usr/bin/tool"):
            manager = JavInfoImportManager(storage_dir=Path(tmp), command_runner=Runner())
            result = await manager.preflight(
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "r18",
                    "maintenance_database": "postgres",
                    "user": "javhub",
                    "password": "",
                },
                expected_size=1,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["checks"]["database"]["target_exists"])


class JavInfoImportRouterTest(unittest.TestCase):
    def _client(self, manager):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.javinfo_imports import router

        app = FastAPI()
        app.include_router(router)
        patcher = patch("routers.javinfo_imports.get_import_manager", return_value=manager)
        patcher.start()
        self.addCleanup(patcher.stop)
        return TestClient(app)

    def test_preflight_endpoint_merges_saved_config_defaults(self):
        class Manager:
            async def preflight(self, settings, *, expected_size=0):
                self.settings = settings
                self.expected_size = expected_size
                return {"ok": True, "checks": {"database": {"ok": True}}}

        manager = Manager()
        with patch("config.config._config", {"javinfo": {"import_db": {"database": "r18_saved"}}}):
            client = self._client(manager)
            response = client.post("/api/v1/javinfo/imports/preflight", json={"expected_size": 123})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(manager.settings["database"], "r18_saved")
        self.assertEqual(manager.settings["host"], "localhost")
        self.assertEqual(manager.expected_size, 123)

    def test_preflight_endpoint_preserves_saved_password_when_ui_sends_blank(self):
        class Manager:
            async def preflight(self, settings, *, expected_size=0):
                self.settings = settings
                return {"ok": True, "checks": {"database": {"ok": True}}}

        manager = Manager()
        with patch(
            "config.config._config",
            {"javinfo": {"import_db": {"user": "javhub", "password": "saved-secret"}}},
        ):
            client = self._client(manager)
            response = client.post(
                "/api/v1/javinfo/imports/preflight",
                json={"import_db": {"host": "postgres", "password": ""}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(manager.settings["host"], "postgres")
        self.assertEqual(manager.settings["user"], "javhub")
        self.assertEqual(manager.settings["password"], "saved-secret")

    def test_create_job_conflict_returns_409(self):
        from services.javinfo_import import JavInfoImportConflict

        class Manager:
            def create_job(self, *args, **kwargs):
                raise JavInfoImportConflict("busy")

        client = self._client(Manager())
        response = client.post(
            "/api/v1/javinfo/imports/jobs",
            json={"filename": "r18.dump", "file_size": 10, "confirm_replace": True},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "busy")

    def test_upload_endpoint_streams_raw_body_to_manager(self):
        class Manager:
            def __init__(self):
                self.saved = b""

            async def save_upload(self, job_id, chunks):
                async for chunk in chunks:
                    self.saved += chunk
                return {
                    "id": job_id,
                    "status": "uploaded",
                    "uploaded_bytes": len(self.saved),
                    "sha256": hashlib.sha256(self.saved).hexdigest(),
                }

            async def restore_job(self, job_id):
                self.restore_job_id = job_id
                return {"id": job_id, "status": "completed"}

        manager = Manager()
        client = self._client(manager)
        response = client.put(
            "/api/v1/javinfo/imports/jobs/7/upload",
            content=b"abcdef",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Filename": "r18.dump",
                "X-File-Size": "6",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(manager.saved, b"abcdef")
        self.assertEqual(response.json()["uploaded_bytes"], 6)

    def test_upload_endpoint_streams_sql_gzip_body_to_restore_manager(self):
        class Manager:
            def __init__(self):
                self.saved = b""

            def get_job(self, job_id):
                return {"id": job_id, "filename": "r18.sql.gz", "status": "pending"}

            async def restore_upload_stream(self, job_id, chunks):
                async for chunk in chunks:
                    self.saved += chunk
                return {"id": job_id, "status": "completed", "uploaded_bytes": len(self.saved)}

        manager = Manager()
        client = self._client(manager)
        response = client.put(
            "/api/v1/javinfo/imports/jobs/7/upload",
            content=b"compressed-sql",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Filename": "r18.sql.gz",
                "X-File-Size": "14",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(manager.saved, b"compressed-sql")
        self.assertEqual(response.json()["status"], "completed")

    def test_chunk_upload_endpoint_passes_offset_headers_to_manager(self):
        class Manager:
            async def save_upload_chunk(self, job_id, chunk, *, offset, total_size):
                self.args = (job_id, chunk, offset, total_size)
                return {"id": job_id, "status": "uploading", "uploaded_bytes": offset + len(chunk)}

        manager = Manager()
        client = self._client(manager)
        response = client.put(
            "/api/v1/javinfo/imports/jobs/7/upload/chunks/0",
            content=b"abcdef",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Chunk-Offset": "0",
                "X-Total-Size": "12",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(manager.args, (7, b"abcdef", 0, 12))
        self.assertEqual(response.json()["uploaded_bytes"], 6)

    def test_finalize_upload_endpoint_starts_restore_after_upload_completion(self):
        class Manager:
            async def finalize_upload(self, job_id):
                self.finalized_job_id = job_id
                return {"id": job_id, "status": "uploaded", "uploaded_bytes": 6}

            async def restore_job(self, job_id):
                self.restore_job_id = job_id
                return {"id": job_id, "status": "completed"}

        manager = Manager()
        client = self._client(manager)
        response = client.post("/api/v1/javinfo/imports/jobs/7/upload/complete")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "uploaded")
        self.assertEqual(manager.finalized_job_id, 7)


class ConfigExportRouterTest(unittest.TestCase):
    def test_config_export_downloads_sanitized_yaml(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.config import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "routers.config.config.get_all",
            return_value={
                "javinfo": {
                    "api_url": "http://javinfoapi:18080",
                    "import_db": {
                        "host": "postgres",
                        "user": "javhub",
                        "password": "secret",
                    },
                },
                "telegram": {"bot_token": "secret-token"},
            },
        ):
            response = TestClient(app).get("/api/v1/config/export")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("javhub-config.yaml", response.headers["content-disposition"])
        self.assertIn("application/x-yaml", response.headers["content-type"])
        text = response.text
        self.assertIn("javinfo:", text)
        self.assertIn("host: postgres", text)
        self.assertIn("user: javhub", text)
        self.assertNotIn("password", text)
        self.assertNotIn("bot_token", text)
