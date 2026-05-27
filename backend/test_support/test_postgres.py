from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from test_support.postgres import TempPostgresMixin


DB_ENV = {
    "JAVHUB_DB_HOST": "test-host",
    "JAVHUB_DB_PORT": "15432",
    "JAVHUB_DB_USER": "test-user",
    "JAVHUB_DB_PASSWORD": "test-password",
    "JAVHUB_DB_NAME": "javhub_test_deadbeef",
    "JAVHUB_DB_MAINTENANCE_DATABASE": "postgres",
}


class TempPostgresSetupFailureTest(unittest.TestCase):
    def _restore_env(self, previous: dict[str, str | None]) -> None:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _case(self):
        class Case(TempPostgresMixin, unittest.TestCase):
            def runTest(self):
                pass

        return Case(methodName="runTest")

    def test_setup_drops_database_and_restores_env_when_init_db_fails(self):
        previous = {key: os.environ.get(key) for key in DB_ENV}
        settings = {
            "host": DB_ENV["JAVHUB_DB_HOST"],
            "port": 15432,
            "user": DB_ENV["JAVHUB_DB_USER"],
            "password": DB_ENV["JAVHUB_DB_PASSWORD"],
            "database": DB_ENV["JAVHUB_DB_NAME"],
            "maintenance_database": DB_ENV["JAVHUB_DB_MAINTENANCE_DATABASE"],
        }

        try:
            with (
                patch("test_support.postgres.create_test_database", return_value=(DB_ENV["JAVHUB_DB_NAME"], settings)),
                patch("test_support.postgres.drop_test_database") as drop_test_database,
                patch("config.config.reload"),
                patch("database.init_db", side_effect=RuntimeError("init boom")),
            ):
                with self.assertRaisesRegex(RuntimeError, "init boom"):
                    self._case().setUp()

                drop_test_database.assert_called_once_with(DB_ENV["JAVHUB_DB_NAME"], settings)
                self.assertEqual({key: os.environ.get(key) for key in DB_ENV}, previous)
        finally:
            self._restore_env(previous)

    def test_setup_drops_database_and_restores_env_when_parent_setup_fails(self):
        previous = {key: os.environ.get(key) for key in DB_ENV}
        settings = {
            "host": DB_ENV["JAVHUB_DB_HOST"],
            "port": 15432,
            "user": DB_ENV["JAVHUB_DB_USER"],
            "password": DB_ENV["JAVHUB_DB_PASSWORD"],
            "database": DB_ENV["JAVHUB_DB_NAME"],
            "maintenance_database": DB_ENV["JAVHUB_DB_MAINTENANCE_DATABASE"],
        }

        try:
            with (
                patch("test_support.postgres.create_test_database", return_value=(DB_ENV["JAVHUB_DB_NAME"], settings)),
                patch("test_support.postgres.drop_test_database") as drop_test_database,
                patch("config.config.reload"),
                patch("database.init_db"),
                patch("test_support.cache.FakeRedisMixin.setUp", side_effect=RuntimeError("redis boom")),
            ):
                with self.assertRaisesRegex(RuntimeError, "redis boom"):
                    self._case().setUp()

                drop_test_database.assert_called_once_with(DB_ENV["JAVHUB_DB_NAME"], settings)
                self.assertEqual({key: os.environ.get(key) for key in DB_ENV}, previous)
        finally:
            self._restore_env(previous)
