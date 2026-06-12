from __future__ import annotations

import threading
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from test_support.client import ASGIClient, create_router_test_client


class HealthRouteTest(unittest.TestCase):
    def _client(self) -> ASGIClient:
        from routers.health import router

        return create_router_test_client(router)

    def test_health_stays_lightweight_liveness(self):
        with patch("routers.health.get_db_orig", create=True) as get_db_orig, \
            patch("routers.health.cache", create=True) as cache_module:
            response = self._client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        get_db_orig.assert_not_called()
        cache_module.get_stats.assert_not_called()

    def test_readiness_returns_dependency_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_stats = {
                "backend": "redis",
                "active_entries": 4,
                "expired_entries": 1,
                "total_entries": 5,
                "singleflight_locks": 2,
            }
            cfg = SimpleNamespace(
                config_loaded=True,
                config_load_error="",
                config_path=Path(tmp) / "config.yaml",
                javinfo_api_url="http://localhost:18080",
                _config={
                    "downloaders": {
                        "default_id": "qb",
                        "clients": [
                            {"id": "qb", "type": "qbittorrent", "enabled": True},
                            {"id": "tr", "type": "transmission", "enabled": False},
                        ],
                    },
                    "openlist": {},
                },
                openlist_api_url="",
                openlist_username="",
                openlist_password="",
                openlist_token="",
                openlist_default_path="",
                javhub_database={
                    "host": "state-postgres",
                    "port": 5432,
                    "database": "javhub",
                    "user": "javhub",
                    "password": "",
                },
            )

            cache_module = SimpleNamespace(get_stats=Mock(return_value=cache_stats))
            scheduler_state = {
                "enabled": True,
                "policy": "rules",
                "effective_enabled": True,
                "disabled_reason": "",
                "running": False,
                "next_run_time": None,
            }

            with patch("routers.health.config", cfg, create=True), \
                patch("routers.health.get_db_orig", create=True) as get_db_orig, \
                patch("routers.health.cache", cache_module, create=True), \
                patch("routers.health._probe_javinfo", new=AsyncMock(return_value={"reachable": True, "version": "1.2.3", "error": ""})), \
                patch("routers.health._source_registry_summary", Mock(return_value={"registered": 3, "available": 2, "error": ""})), \
                patch("routers.health._scheduler_summary", Mock(return_value=scheduler_state)):
                response = self._client().get("/health/readiness")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {
                "status": "ok",
                "config": {
                    "loaded": True,
                    "error": "",
                    "path": str(cfg.config_path),
                },
                "database": {
                    "backend": "postgres",
                    "connectable": True,
                    "host": "state-postgres",
                    "port": 5432,
                    "database": "javhub",
                    "user": "javhub",
                    "error": "",
                },
                "javinfo": {
                    "api_url_configured": True,
                    "api_url": "http://localhost:18080",
                    "legacy": False,
                    "reachable": True,
                    "version": "1.2.3",
                    "error": "",
                },
                "cache": {
                    "backend": "redis",
                    "active_entries": 4,
                    "expired_entries": 1,
                    "total_entries": 5,
                    "singleflight_locks": 2,
                    "error": "",
                },
                "downloaders": {
                    "default_id": "qb",
                    "default_available": True,
                    "registered": 3,
                    "available": 1,
                    "error": "",
                },
                "sources": {
                    "registered": 3,
                    "available": 2,
                    "error": "",
                    "recent_attempt_count": 0,
                    "latest_attempt_error": "",
                    "latest_attempt_source": "",
                    "latest_attempt_keyword": "",
                },
                "scheduler": scheduler_state,
            })
            get_db_orig.return_value.execute.assert_called_once_with("SELECT 1")
            get_db_orig.return_value.close.assert_called_once()

    def test_readiness_reports_degraded_checks_but_keeps_http_200(self):
        cache_error = RuntimeError("cache unavailable")
        cfg = SimpleNamespace(
            config_loaded=False,
            config_load_error="config file not found",
            config_path=Path("/missing/config.yaml"),
            javinfo_api_url="",
            _config={},
            openlist_api_url="",
            openlist_username="",
            openlist_password="",
            openlist_token="",
            openlist_default_path="",
            javhub_database={
                "host": "state-postgres",
                "port": 5432,
                "database": "javhub",
                "user": "javhub",
                "password": "",
            },
        )
        db_conn = Mock()
        db_conn.execute.side_effect = RuntimeError("database locked")

        cache_module = SimpleNamespace(get_stats=Mock(side_effect=cache_error))

        with patch("routers.health.config", cfg, create=True), \
            patch("routers.health.get_db_orig", Mock(return_value=db_conn), create=True), \
            patch("routers.health.cache", cache_module, create=True), \
                patch("routers.health._probe_javinfo", new=AsyncMock(return_value={"reachable": False, "version": "", "error": "api url not configured"})), \
            patch("routers.health._source_registry_summary", Mock(return_value={"registered": 0, "available": 0, "error": "sources unavailable"})), \
            patch("routers.health._scheduler_summary", Mock(return_value={
                "enabled": False,
                "policy": "manual",
                "effective_enabled": False,
                "disabled_reason": "manual_policy",
                "running": False,
                "next_run_time": None,
            })):
            response = self._client().get("/health/readiness")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "degraded")
        self.assertEqual(body["config"], {
            "loaded": False,
            "error": "config file not found",
            "path": "/missing/config.yaml",
        })
        self.assertEqual(body["database"], {
            "backend": "postgres",
            "connectable": False,
            "host": "state-postgres",
            "port": 5432,
            "database": "javhub",
            "user": "javhub",
            "error": "database locked",
        })
        self.assertEqual(body["javinfo"], {
            "api_url_configured": False,
            "api_url": "",
            "legacy": False,
            "reachable": False,
            "version": "",
            "error": "api url not configured",
        })
        self.assertEqual(body["cache"], {
            "backend": "unknown",
            "active_entries": None,
            "expired_entries": None,
            "total_entries": None,
            "singleflight_locks": None,
            "error": "cache unavailable",
        })
        self.assertEqual(body["downloaders"]["default_available"], False)
        self.assertEqual(body["sources"], {
            "registered": 0,
            "available": 0,
            "error": "sources unavailable",
            "recent_attempt_count": 0,
            "latest_attempt_error": "",
            "latest_attempt_source": "",
            "latest_attempt_keyword": "",
        })
        self.assertEqual(body["scheduler"]["disabled_reason"], "manual_policy")
        db_conn.close.assert_called_once()

    def test_readiness_includes_recent_source_attempt_diagnostics(self):
        with patch("routers.health._source_attempt_summary", Mock(return_value={
            "recent_attempt_count": 2,
            "latest_attempt_error": "TimeoutError: slow",
            "latest_attempt_source": "torznab",
            "latest_attempt_keyword": "ABC-123",
        })):
            result = __import__("routers.health", fromlist=["_source_registry_summary"])._source_registry_summary()

        self.assertEqual(result["recent_attempt_count"], 2)
        self.assertEqual(result["latest_attempt_error"], "TimeoutError: slow")
        self.assertEqual(result["latest_attempt_source"], "torznab")
        self.assertEqual(result["latest_attempt_keyword"], "ABC-123")

    def test_downloader_health_accepts_verified_environment_open115_binding(self):
        from routers.health import _downloader_summary

        cfg = SimpleNamespace(
            _config={
                "open115": {"verified": True},
                "downloaders": {"default_id": "open115", "clients": []},
            }
        )
        with patch.dict("os.environ", {"OPEN115_REFRESH_TOKEN": "environment-refresh"}), \
            patch("routers.health.config", cfg):
            summary = _downloader_summary()

        self.assertEqual(summary["default_id"], "open115")
        self.assertTrue(summary["default_available"])
        self.assertEqual(summary["available"], 1)

    def test_local_launchagent_javinfo_url_is_not_marked_legacy(self):
        cfg = SimpleNamespace(
            config_loaded=True,
            config_load_error="",
            config_path=Path("/tmp/config.yaml"),
            javinfo_api_url="http://127.0.0.1:8080",
            _config={
                "downloaders": {
                    "default_id": "openlist",
                    "clients": [{"id": "openlist", "type": "openlist", "enabled": True}],
                },
            },
            openlist_api_url="",
            openlist_username="",
            openlist_password="",
            openlist_token="",
            openlist_default_path="",
            javhub_database={
                "host": "state-postgres",
                "port": 5432,
                "database": "javhub",
                "user": "javhub",
                "password": "",
            },
        )

        with patch("routers.health.config", cfg, create=True), \
            patch("routers.health.get_db_orig", create=True), \
            patch("routers.health.cache", SimpleNamespace(get_stats=Mock(return_value={
                "backend": "redis",
                "active_entries": 1,
                "expired_entries": 0,
                "total_entries": 1,
                "singleflight_locks": 0,
            })), create=True), \
            patch("routers.health._probe_javinfo", new=AsyncMock(return_value={"reachable": True, "version": "", "error": ""})), \
            patch("routers.health._source_registry_summary", Mock(return_value={"registered": 1, "available": 1, "error": ""})), \
            patch("routers.health._scheduler_summary", Mock(return_value={
                "enabled": True,
                "policy": "rules",
                "effective_enabled": True,
                "disabled_reason": "",
                "running": False,
                "next_run_time": None,
            })):
            response = self._client().get("/health/readiness")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["javinfo"]["api_url"], "http://127.0.0.1:8080")
        self.assertFalse(body["javinfo"]["legacy"])
        self.assertEqual(body["javinfo"]["error"], "")


class HealthReadinessConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_probes_javinfo_while_database_check_is_running(self):
        from routers import health

        release_db = threading.Event()
        probe_observation: dict[str, bool] = {}
        cfg = SimpleNamespace(
            config_loaded=True,
            config_load_error="",
            config_path=Path("/tmp/config.yaml"),
            javinfo_api_url="http://127.0.0.1:8080",
            _config={
                "downloaders": {
                    "default_id": "openlist",
                    "clients": [{"id": "openlist", "type": "openlist", "enabled": True}],
                },
            },
        )

        def database_status():
            release_db.wait(timeout=1)
            return {
                "backend": "postgres",
                "connectable": True,
                "host": "state-postgres",
                "port": 5432,
                "database": "javhub",
                "user": "javhub",
                "error": "",
            }

        async def probe_javinfo(_api_url: str):
            probe_observation["db_still_running"] = not release_db.is_set()
            return {"reachable": True, "version": "1.2.3", "error": ""}

        timer = threading.Timer(0.05, release_db.set)
        timer.start()
        try:
            with patch("routers.health.config", cfg, create=True), \
                patch("routers.health._database_status", Mock(side_effect=database_status)), \
                patch("routers.health._probe_javinfo", new=AsyncMock(side_effect=probe_javinfo)), \
                patch("routers.health._cache_status", Mock(return_value={"backend": "redis", "error": ""})), \
                patch("routers.health._downloader_summary", Mock(return_value={
                    "default_id": "openlist",
                    "default_available": True,
                    "registered": 1,
                    "available": 1,
                    "error": "",
                })), \
                patch("routers.health._source_registry_summary", Mock(return_value={"registered": 1, "available": 1, "error": ""})), \
                patch("routers.health._scheduler_summary", Mock(return_value={
                    "enabled": True,
                    "policy": "rules",
                    "effective_enabled": True,
                    "disabled_reason": "",
                    "running": False,
                    "next_run_time": None,
                })):
                response = await health.readiness_check()
        finally:
            release_db.set()
            timer.cancel()

        self.assertEqual(response["status"], "ok")
        self.assertTrue(probe_observation["db_still_running"])


if __name__ == "__main__":
    unittest.main()
