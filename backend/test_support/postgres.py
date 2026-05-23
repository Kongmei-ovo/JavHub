from __future__ import annotations

import os
import uuid
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

    def tearDown(self):
        from config import config

        super().tearDown()
        self.env_patch.stop()
        config.reload()
        drop_test_database(self.test_db_name, self.test_db_settings)
