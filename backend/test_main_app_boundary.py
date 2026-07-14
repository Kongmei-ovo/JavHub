from __future__ import annotations

import importlib
import unittest
from unittest.mock import AsyncMock, Mock, patch

import anyio

from test_support.client import create_test_client, load_main_app_without_db


class MainAppBoundaryTest(unittest.TestCase):
    def test_importing_assembled_app_does_not_install_database_log_bridge(self):
        with patch("database.init_db"), patch(
            "services.db_log_bridge.install_db_log_bridge"
        ) as install_bridge:
            module = importlib.import_module("main")
            importlib.reload(module)

        install_bridge.assert_not_called()
        self.assertNotIsInstance(getattr(module, "install_db_log_bridge", None), Mock)

    def test_loading_assembled_app_does_not_leak_database_mock(self):
        load_main_app_without_db()

        module = importlib.import_module("main")
        self.assertNotIsInstance(getattr(module, "init_db", None), Mock)

    def test_loading_assembled_app_rebuilds_cors_for_current_origin(self):
        from config import config

        def preflight(origin: str):
            return create_test_client(load_main_app_without_db()).request(
                "OPTIONS",
                "/Items",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "HEAD",
                    "Access-Control-Request-Headers": "X-Emby-Token",
                },
            )

        first_origin = "http://first.example"
        second_origin = "http://second.example"
        with patch.object(config, "_config", {"server": {"frontend_origin": first_origin}}):
            first = preflight(first_origin)
        with patch.object(config, "_config", {"server": {"frontend_origin": second_origin}}):
            second = preflight(second_origin)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.headers["access-control-allow-origin"], first_origin)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.headers["access-control-allow-origin"], second_origin)

    def test_assembled_app_registers_source_config_and_keeps_source_health(self):
        app = load_main_app_without_db()
        client = create_test_client(app)
        snapshot = {"builtins": [], "sources": [], "types": ["torznab", "avdb"]}

        with patch(
            "routers.source_management.get_source_snapshot",
            return_value=snapshot,
        ), patch("routers.source_health.source_health_summary", return_value=[]):
            config_response = client.get("/api/v1/sources/config")
            health_response = client.get("/api/v1/sources/health")

        self.assertEqual(config_response.status_code, 200, config_response.text)
        self.assertEqual(config_response.json(), snapshot)
        self.assertEqual(health_response.status_code, 200, health_response.text)
        self.assertEqual(health_response.json(), [])

    def test_startup_installs_database_log_bridge(self):
        with patch("database.init_db"):
            module = importlib.import_module("main")
        start_session_manager = AsyncMock()
        with patch("services.db_log_bridge.install_db_log_bridge") as install_bridge, \
            patch("scheduler.tasks.start_scheduler"), \
            patch("services.singbox.manager.reconcile", new=AsyncMock()), \
            patch("routers.config._push_proxy_to_javinfo", new=AsyncMock()), \
            patch("sources.register_all_sources"), \
            patch(
                "services.cf_solver.start_session_manager",
                new=start_session_manager,
                create=True,
            ):
            anyio.run(module.startup_event)

        install_bridge.assert_called_once_with()
        start_session_manager.assert_awaited_once_with()

    def test_shutdown_closes_cf_session_manager(self):
        with patch("database.init_db"):
            module = importlib.import_module("main")
        info_client = Mock()
        info_client.close = AsyncMock()
        close_session_manager = AsyncMock()
        with patch("services.singbox.manager.stop"), \
            patch("scheduler.tasks.stop_scheduler"), \
            patch("modules.info_client.get_info_client", return_value=info_client), \
            patch("services.open115.open115_client.close", new=AsyncMock()), \
            patch("routers.playback.playback_hls_client.aclose", new=AsyncMock()), \
            patch(
                "services.cf_solver.close_session_manager",
                new=close_session_manager,
                create=True,
            ):
            anyio.run(module.shutdown_event)

        close_session_manager.assert_awaited_once_with()

    def test_shutdown_stops_scheduler_before_closing_loop_owned_clients(self):
        with patch("database.init_db"):
            module = importlib.import_module("main")
        calls = []
        info_client = Mock()

        async def close_info():
            calls.append("info")

        async def close_open115():
            calls.append("open115")

        info_client.close = AsyncMock(side_effect=close_info)
        with patch("services.singbox.manager.stop"), \
            patch("scheduler.tasks.stop_scheduler", side_effect=lambda: calls.append("scheduler")), \
            patch("modules.info_client.get_info_client", return_value=info_client), \
            patch("services.open115.open115_client.close", new=AsyncMock(side_effect=close_open115)), \
            patch("services.cache.close_backend", new=AsyncMock()), \
            patch("routers.playback.playback_hls_client.aclose", new=AsyncMock()), \
            patch("services.cf_solver.close_session_manager", new=AsyncMock(), create=True):
            anyio.run(module.shutdown_event)

        self.assertEqual(calls, ["scheduler", "info", "open115"])

    def test_openapi_has_unique_first_party_operations_and_no_emby_paths(self):
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            app = load_main_app_without_db()
            app.openapi_schema = None
            schema = app.openapi()

        operation_ids = [
            operation["operationId"]
            for path_item in schema["paths"].values()
            for operation in path_item.values()
            if isinstance(operation, dict) and "operationId" in operation
        ]
        duplicate_warnings = [
            item for item in caught if "Duplicate Operation ID" in str(item.message)
        ]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        self.assertEqual(duplicate_warnings, [])
        self.assertIn("/api/v1/video-variants/index/jobs", schema["paths"])
        self.assertIn("/api/v1/jobs", schema["paths"])
        self.assertNotIn("/System/Info/Public", schema["paths"])
        self.assertNotIn("/emby/System/Info/Public", schema["paths"])
        self.assertNotIn("/emby", schema["paths"])


if __name__ == "__main__":
    unittest.main()
