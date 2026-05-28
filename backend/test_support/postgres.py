from __future__ import annotations

import os
import uuid
from contextlib import suppress
from typing import Any, Callable
from unittest.mock import patch

import psycopg2
from psycopg2 import sql

from test_support.cache import FakeRedisMixin


def _settings(database: str | None = None) -> dict:
    return {
        "host": os.getenv("JAVHUB_TEST_DB_HOST") or os.getenv("JAVHUB_DB_HOST") or "localhost",
        "port": int(os.getenv("JAVHUB_TEST_DB_PORT") or os.getenv("JAVHUB_DB_PORT") or "5432"),
        "user": os.getenv("JAVHUB_TEST_DB_USER") or os.getenv("JAVHUB_DB_USER") or "kongmei",
        "password": os.getenv("JAVHUB_TEST_DB_PASSWORD") or os.getenv("JAVHUB_DB_PASSWORD") or "",
        "maintenance_database": (
            os.getenv("JAVHUB_TEST_DB_MAINTENANCE_DATABASE")
            or os.getenv("JAVHUB_DB_MAINTENANCE_DATABASE")
            or "postgres"
        ),
        "database": database or "javhub_test",
    }


CallLog = list[tuple[str, tuple[Any, ...]]]


class RecordingCursor:
    def __init__(self, *, calls: CallLog | None = None, executed: list[str] | None = None):
        self.calls = calls if calls is not None else []
        self.executed = executed if executed is not None else []
        self.rowcount = 0

    def execute(self, sql: Any, params: Any = None) -> None:
        sql_text = str(sql)
        self.executed.append(sql_text)
        args = (sql_text,) if params is None else (sql_text, params)
        self.calls.append(("execute", args))


class RecordingConnection:
    def __init__(self, calls: CallLog | None = None, cursor: object | None = None):
        self.calls = calls if calls is not None else []
        self.cursor_obj = cursor if cursor is not None else RecordingCursor(calls=self.calls)

    def cursor(self) -> object:
        self.calls.append(("cursor", ()))
        return self.cursor_obj

    def commit(self) -> None:
        self.calls.append(("commit", ()))

    def rollback(self) -> None:
        self.calls.append(("rollback", ()))

    def close(self) -> None:
        self.calls.append(("close", ()))


def record_call(name: str, calls: CallLog) -> Callable[..., None]:
    def record(*args: Any) -> None:
        calls.append((name, args))

    return record


def make_recording_connection(
    *,
    calls: CallLog | None = None,
    executed: list[str] | None = None,
    cursor: object | None = None,
) -> RecordingConnection:
    call_log = calls if calls is not None else []
    cursor_obj = cursor if cursor is not None else RecordingCursor(calls=call_log, executed=executed)
    return RecordingConnection(call_log, cursor_obj)


def create_test_database(prefix: str = "javhub_test") -> tuple[str, dict]:
    database = f"{prefix}_{uuid.uuid4().hex[:12]}"
    settings = _settings(database)
    conn = psycopg2.connect(
        host=settings["host"],
        port=settings["port"],
        dbname=settings["maintenance_database"],
        user=settings["user"],
        password=settings["password"],
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    finally:
        conn.close()
    return database, settings


def drop_test_database(database: str, settings: dict) -> None:
    conn = psycopg2.connect(
        host=settings["host"],
        port=settings["port"],
        dbname=settings["maintenance_database"],
        user=settings["user"],
        password=settings["password"],
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (database,),
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
    finally:
        conn.close()


class TempPostgresMixin(FakeRedisMixin):
    def setUp(self):
        self.test_db_name = None
        self.test_db_settings = None
        self.env_patch = None
        try:
            self.test_db_name, self.test_db_settings = create_test_database()
            self.env_patch = patch.dict(
                os.environ,
                {
                    "JAVHUB_DB_HOST": self.test_db_settings["host"],
                    "JAVHUB_DB_PORT": str(self.test_db_settings["port"]),
                    "JAVHUB_DB_USER": self.test_db_settings["user"],
                    "JAVHUB_DB_PASSWORD": self.test_db_settings["password"],
                    "JAVHUB_DB_NAME": self.test_db_settings["database"],
                    "JAVHUB_DB_MAINTENANCE_DATABASE": self.test_db_settings["maintenance_database"],
                },
                clear=False,
            )
            self.env_patch.start()

            from config import config

            config.reload()
            from database import init_db

            init_db()
            super().setUp()
        except Exception:
            self._cleanup_temp_postgres(suppress_config_errors=True)
            raise

    def tearDown(self):
        try:
            super().tearDown()
        finally:
            self._cleanup_temp_postgres()

    def _cleanup_temp_postgres(self, *, suppress_config_errors: bool = False) -> None:
        env_patch = getattr(self, "env_patch", None)
        if env_patch is not None:
            env_patch.stop()
            self.env_patch = None

        from config import config

        if suppress_config_errors:
            with suppress(Exception):
                config.reload()
        else:
            config.reload()

        test_db_name = getattr(self, "test_db_name", None)
        test_db_settings = getattr(self, "test_db_settings", None)
        if test_db_name and test_db_settings:
            drop_test_database(test_db_name, test_db_settings)
            self.test_db_name = None
            self.test_db_settings = None
