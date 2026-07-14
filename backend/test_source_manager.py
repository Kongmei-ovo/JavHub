from __future__ import annotations

import copy
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from config import Config, DEFAULT_TORZNAB_SOURCE
from services import source_manager


class SourceManagerTest(unittest.TestCase):
    def setUp(self):
        self.config_patcher = patch.object(
            source_manager.config,
            "_config",
            {"unrelated": {"keep": True}, "sources": self._base_sources()},
        )
        self.config_patcher.start()
        self.env_patcher = patch.dict(
            os.environ,
            {"JAVHUB_TORZNAB_API_KEY": ""},
            clear=False,
        )
        self.env_patcher.start()
        self.avdb_status = patch.object(
            source_manager,
            "get_avdb_status",
            return_value={"available": False, "status": "never", "record_count": 0},
        ).start()
        self.real_refresh_runtime = source_manager._refresh_runtime
        self.refresh_runtime = patch.object(source_manager, "_refresh_runtime").start()
        self.persisted_sources: list[dict] = []
        self.replace_sources = patch.object(
            source_manager.config,
            "replace_sources",
            side_effect=self._replace_sources,
        ).start()

    def tearDown(self):
        patch.stopall()

    @staticmethod
    def _base_sources() -> dict:
        return {
            "torznab": {
                "enabled": True,
                "name": "Prowlarr",
                "base_url": "https://prowlarr.test",
                "api_key": "legacy-secret",
                "indexer": "all",
                "categories": "5000",
                "limit": 25,
                "timeout": 20,
            },
            "torznab_instances": [
                {
                    "id": "jackett-id",
                    "kind": "jackett",
                    "enabled": True,
                    "name": "Jackett",
                    "base_url": "https://jackett.test",
                    "api_key": "instance-secret",
                    "indexer": "all",
                    "categories": "",
                    "limit": 30,
                    "timeout": 12,
                }
            ],
            "future_source": {"keep": "unchanged"},
        }

    def _replace_sources(self, sources: dict) -> None:
        saved = copy.deepcopy(sources)
        self.persisted_sources.append(saved)
        source_manager.config._config["sources"] = saved

    def _set_sources(self, sources: dict) -> None:
        source_manager.config._config = {
            "unrelated": {"keep": True},
            "sources": copy.deepcopy(sources),
        }

    def assert_error(self, status_code: int, func, *args, **kwargs):
        with self.assertRaises(source_manager.SourceConfigError) as caught:
            func(*args, **kwargs)
        self.assertEqual(caught.exception.status_code, status_code)
        self.assertTrue(str(caught.exception))
        return caught.exception

    def test_snapshot_has_builtin_stable_ids_and_never_exposes_api_keys(self):
        snapshot = source_manager.get_source_snapshot(
            avdb_status={"available": False, "status": "never"}
        )

        self.assertEqual(snapshot["types"], ["torznab", "avdb"])
        self.assertEqual(snapshot["builtins"][0]["id"], "m3u8")
        self.assertEqual(snapshot["builtins"][0]["name"], "在线 M3U8")
        self.assertTrue(snapshot["builtins"][0]["builtin"])
        self.assertTrue(snapshot["builtins"][0]["enabled"])
        self.assertTrue(snapshot["builtins"][0]["available"])
        self.assertEqual(
            [item["id"] for item in snapshot["sources"]],
            [source_manager.LEGACY_TORZNAB_ID, "jackett-id"],
        )
        self.assertEqual(snapshot["sources"][1]["kind"], "jackett")
        for item in snapshot["sources"]:
            self.assertNotIn("api_key", item)
            self.assertIn("api_key_configured", item)
            self.assertTrue(item["api_key_configured"])

    def test_updating_instance_with_blank_key_preserves_secret_and_id(self):
        snapshot = source_manager.update_source(
            "jackett-id",
            {
                "enabled": False,
                "name": "  Backup Jackett  ",
                "base_url": "https://backup-jackett.test/",
                "api_key": "",
                "indexer": "7",
                "categories": "5000,5070",
                "limit": 999,
                "timeout": 0,
                "kind": "prowlarr",
            },
        )

        saved = self.persisted_sources[-1]["torznab_instances"][0]
        self.assertEqual(saved["id"], "jackett-id")
        self.assertEqual(saved["api_key"], "instance-secret")
        self.assertEqual(saved["name"], "Backup Jackett")
        self.assertEqual(saved["base_url"], "https://backup-jackett.test/")
        self.assertEqual(saved["indexer"], "7")
        self.assertEqual(saved["categories"], "5000,5070")
        self.assertEqual(saved["limit"], 100)
        self.assertEqual(saved["timeout"], 1)
        self.assertFalse(saved["enabled"])
        self.assertEqual(saved["kind"], "prowlarr")
        self.assertIn("jackett-id", [item["id"] for item in snapshot["sources"]])
        self.assertNotIn("api_key", snapshot["sources"][1])
        self.refresh_runtime.assert_called_once_with(avdb_changed=False)

    def test_torznab_names_are_trimmed_casefold_unique_and_avdb_is_reserved(self):
        self.assert_error(
            409,
            source_manager.create_source,
            {
                "type": "torznab",
                "name": "  jAcKeTt  ",
                "base_url": "https://other.test",
                "api_key": "new-secret",
            },
        )
        self.assert_error(
            409,
            source_manager.create_source,
            {
                "type": "torznab",
                "name": "  AVDB  ",
                "base_url": "https://other.test",
                "api_key": "new-secret",
            },
        )
        self.replace_sources.assert_not_called()

    def test_unique_names_use_the_same_fallbacks_as_runtime_registration(self):
        sources = self._base_sources()
        sources["torznab"].pop("name")
        sources["torznab_instances"][0]["name"] = "  "
        self._set_sources(sources)

        self.assert_error(
            409,
            source_manager.create_source,
            {
                "type": "torznab",
                "name": " TORZNAB ",
                "base_url": "https://duplicate.test",
                "api_key": "secret",
            },
        )
        self.assert_error(
            409,
            source_manager.create_source,
            {
                "type": "torznab",
                "name": "torznab-2",
                "base_url": "https://duplicate.test",
                "api_key": "secret",
            },
        )
        self.replace_sources.assert_not_called()

    def test_deleting_instance_and_legacy_source_affects_only_target(self):
        original_legacy = copy.deepcopy(source_manager.config._config["sources"]["torznab"])
        source_manager.delete_source("jackett-id")
        saved = self.persisted_sources[-1]
        self.assertEqual(saved["torznab"], original_legacy)
        self.assertEqual(saved["torznab_instances"], [])

        self._set_sources(self._base_sources())
        self.persisted_sources.clear()
        source_manager.delete_source(source_manager.LEGACY_TORZNAB_ID)
        saved = self.persisted_sources[-1]
        self.assertEqual(saved["torznab"], DEFAULT_TORZNAB_SOURCE)
        self.assertEqual(saved["torznab_instances"][0]["id"], "jackett-id")

    def test_avdb_create_is_singleton_and_delete_only_updates_flags(self):
        sources = self._base_sources()
        sources["avdb"] = {
            "enabled": False,
            "sync_enabled": False,
            "repository": "pinned/repository",
            "interval_hours": 24,
            "internal_guard": "keep-me",
        }
        self._set_sources(sources)

        snapshot = source_manager.create_source(
            {"type": "avdb", "enabled": True, "available": True}
        )
        saved = self.persisted_sources[-1]["avdb"]
        self.assertFalse(saved["enabled"])
        self.assertTrue(saved["sync_enabled"])
        self.assertEqual(saved["repository"], "pinned/repository")
        self.assertEqual(saved["internal_guard"], "keep-me")
        avdb_row = next(item for item in snapshot["sources"] if item["id"] == "avdb")
        self.assertFalse(avdb_row["enabled"])
        self.assertTrue(avdb_row["sync_enabled"])
        self.refresh_runtime.assert_called_once_with(avdb_changed=True)

        self.assert_error(409, source_manager.create_source, {"type": "avdb"})
        self.refresh_runtime.reset_mock()
        source_manager.delete_source("avdb")
        saved = self.persisted_sources[-1]["avdb"]
        self.assertFalse(saved["enabled"])
        self.assertFalse(saved["sync_enabled"])
        self.assertEqual(saved["internal_guard"], "keep-me")
        self.refresh_runtime.assert_called_once_with(avdb_changed=True)

    def test_create_rolls_back_config_when_runtime_refresh_fails_and_can_retry(self):
        old_sources = copy.deepcopy(source_manager.config._config["sources"])
        payload = {
            "type": "torznab",
            "name": "Rollback Indexer",
            "base_url": "https://rollback-indexer.test",
            "api_key": "rollback-secret",
        }
        refresh_error = RuntimeError("runtime refresh failed")
        self.refresh_runtime.side_effect = [refresh_error, None]

        with self.assertRaises(RuntimeError) as caught:
            source_manager.create_source(payload)

        self.assertIs(caught.exception, refresh_error)
        self.assertEqual(self.replace_sources.call_count, 2)
        first_saved = self.replace_sources.call_args_list[0].args[0]
        self.assertIn(
            "Rollback Indexer",
            [item["name"] for item in first_saved["torznab_instances"]],
        )
        self.assertEqual(self.replace_sources.call_args_list[1].args[0], old_sources)
        self.assertEqual(source_manager.config._config["sources"], old_sources)
        self.assertEqual(self.refresh_runtime.call_count, 2)

        self.replace_sources.reset_mock()
        self.refresh_runtime.reset_mock(side_effect=True)
        source_manager.create_source(payload)
        names = [
            item["name"]
            for item in source_manager.config._config["sources"]["torznab_instances"]
        ]
        self.assertEqual(names.count("Rollback Indexer"), 1)

    def test_avdb_delete_rolls_back_flags_when_runtime_refresh_fails(self):
        sources = self._base_sources()
        sources["avdb"] = {
            "enabled": True,
            "sync_enabled": True,
            "internal_guard": "keep-me",
        }
        self._set_sources(sources)
        old_sources = copy.deepcopy(source_manager.config._config["sources"])
        refresh_error = RuntimeError("scheduler refresh failed")
        self.refresh_runtime.side_effect = [refresh_error, None]

        with self.assertRaises(RuntimeError) as caught:
            source_manager.delete_source("avdb")

        self.assertIs(caught.exception, refresh_error)
        self.assertEqual(self.replace_sources.call_count, 2)
        self.assertFalse(self.replace_sources.call_args_list[0].args[0]["avdb"]["enabled"])
        self.assertFalse(
            self.replace_sources.call_args_list[0].args[0]["avdb"]["sync_enabled"]
        )
        self.assertEqual(self.replace_sources.call_args_list[1].args[0], old_sources)
        self.assertEqual(source_manager.config._config["sources"], old_sources)

        self.replace_sources.reset_mock()
        self.refresh_runtime.reset_mock(side_effect=True)
        source_manager.delete_source("avdb")
        self.assertFalse(source_manager.config._config["sources"]["avdb"]["enabled"])
        self.assertFalse(
            source_manager.config._config["sources"]["avdb"]["sync_enabled"]
        )

    def test_refresh_failure_reports_config_rollback_failure_with_cause(self):
        replace_count = 0

        def fail_rollback(sources: dict) -> None:
            nonlocal replace_count
            replace_count += 1
            if replace_count == 1:
                self._replace_sources(sources)
                return
            raise OSError("config rollback failed")

        self.replace_sources.side_effect = fail_rollback
        self.refresh_runtime.side_effect = RuntimeError("runtime refresh failed")

        with self.assertRaises(RuntimeError) as caught:
            source_manager.create_source(
                {
                    "type": "torznab",
                    "name": "Rollback Failure",
                    "base_url": "https://rollback-failure.test",
                    "api_key": "secret",
                }
            )

        self.assertIn("配置回滚失败", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertEqual(self.replace_sources.call_count, 2)

    def test_avdb_enable_requires_current_backend_availability(self):
        sources = self._base_sources()
        sources["avdb"] = {"enabled": False, "sync_enabled": True, "internal_guard": 1}
        self._set_sources(sources)

        self.avdb_status.return_value = {"status": "never"}
        self.assert_error(
            400,
            source_manager.update_source,
            "avdb",
            {"enabled": True, "available": True},
        )
        self.avdb_status.return_value = {"available": False, "status": "success"}
        self.assert_error(
            400,
            source_manager.update_source,
            "avdb",
            {"enabled": True, "available": True},
        )
        self.replace_sources.assert_not_called()

        self.avdb_status.return_value = {
            "available": True,
            "status": "success",
            "record_count": 123,
        }
        snapshot = source_manager.update_source("avdb", {"enabled": True})
        self.assertTrue(self.persisted_sources[-1]["avdb"]["enabled"])
        row = next(item for item in snapshot["sources"] if item["id"] == "avdb")
        self.assertTrue(row["enabled"])
        self.assertTrue(row["available"])
        self.assertEqual(row["record_count"], 123)
        self.avdb_status.assert_called()

    def test_legacy_instance_id_is_deterministic_secret_free_and_materialized_on_write(self):
        sources = self._base_sources()
        sources["torznab_instances"][0].pop("id")
        self._set_sources(sources)

        first = source_manager.get_source_snapshot(avdb_status={"available": False})
        first_id = first["sources"][1]["id"]
        second = source_manager.get_source_snapshot(avdb_status={"available": False})
        self.assertEqual(second["sources"][1]["id"], first_id)

        source_manager.config._config["sources"]["torznab_instances"][0]["api_key"] = (
            "rotated-secret"
        )
        after_rotation = source_manager.get_source_snapshot(avdb_status={"available": False})
        self.assertEqual(after_rotation["sources"][1]["id"], first_id)

        source_manager.create_source(
            {
                "type": "torznab",
                "name": "NZB Mirror",
                "base_url": "https://mirror.test",
                "api_key": "mirror-secret",
            }
        )
        materialized = self.persisted_sources[-1]["torznab_instances"][0]
        self.assertEqual(materialized["id"], first_id)
        self.assertEqual(materialized["api_key"], "rotated-secret")

    def test_generated_id_does_not_displace_later_unique_existing_id(self):
        sources = self._base_sources()
        sources["torznab"] = copy.deepcopy(DEFAULT_TORZNAB_SOURCE)
        template = sources["torznab_instances"][0]
        preserved_id = "torznab-legacy-preserved"
        generated_id = "torznab-legacy-generated"
        sources["torznab_instances"] = [
            {
                **copy.deepcopy(template),
                "name": "Legacy Indexer",
                "base_url": "https://legacy-indexer.test",
            },
            {
                **copy.deepcopy(template),
                "id": preserved_id,
                "name": "Existing Indexer",
                "base_url": "https://existing-indexer.test",
            },
        ]
        sources["torznab_instances"][0].pop("id")
        self._set_sources(sources)

        def compatible_id(_item, _position, used):
            for candidate in (preserved_id, generated_id):
                if candidate not in used:
                    return candidate
            self.fail("test candidates unexpectedly exhausted")

        with patch.object(
            source_manager,
            "_compatible_instance_id",
            side_effect=compatible_id,
        ):
            first = source_manager.get_source_snapshot(avdb_status={"available": False})
            second = source_manager.get_source_snapshot(avdb_status={"available": False})
            first_ids = [item["id"] for item in first["sources"]]

            self.assertEqual(first_ids[1], preserved_id)
            self.assertNotEqual(first_ids[0], preserved_id)
            self.assertEqual([item["id"] for item in second["sources"]], first_ids)

            source_manager.create_source(
                {
                    "type": "torznab",
                    "name": "New Indexer",
                    "base_url": "https://new-indexer.test",
                    "api_key": "new-secret",
                }
            )

        materialized_ids = [
            item["id"] for item in self.persisted_sources[-1]["torznab_instances"][:2]
        ]
        self.assertEqual(materialized_ids, first_ids)

    def test_reserved_and_duplicate_instance_ids_get_unique_compatible_ids(self):
        sources = self._base_sources()
        sources["torznab"] = copy.deepcopy(DEFAULT_TORZNAB_SOURCE)
        template = sources["torznab_instances"][0]
        existing_ids = ["avdb", "m3u8", source_manager.LEGACY_TORZNAB_ID, "duplicate", "duplicate"]
        sources["torznab_instances"] = [
            {
                **copy.deepcopy(template),
                "id": existing_id,
                "name": f"Indexer {position}",
                "base_url": f"https://indexer-{position}.test",
            }
            for position, existing_id in enumerate(existing_ids)
        ]
        self._set_sources(sources)

        first = source_manager.get_source_snapshot(avdb_status={"available": False})
        second = source_manager.get_source_snapshot(avdb_status={"available": False})
        first_ids = [item["id"] for item in first["sources"]]
        self.assertEqual([item["id"] for item in second["sources"]], first_ids)
        self.assertEqual(len(first_ids), len(set(first_ids)))
        self.assertTrue({"avdb", "m3u8", source_manager.LEGACY_TORZNAB_ID}.isdisjoint(first_ids))
        self.assertNotEqual(first_ids[3], "duplicate")
        self.assertNotEqual(first_ids[4], "duplicate")

        source_manager.create_source(
            {
                "type": "torznab",
                "name": "New Indexer",
                "base_url": "https://new-indexer.test",
                "api_key": "new-secret",
            }
        )
        materialized_ids = [
            item["id"] for item in self.persisted_sources[-1]["torznab_instances"][:-1]
        ]
        self.assertEqual(materialized_ids, first_ids)

    def test_unique_existing_id_is_reserved_before_compatible_ids_are_generated(self):
        instances = [
            {"name": "Missing ID"},
            {"id": "future-unique-id", "name": "Existing ID"},
        ]

        def compatible_id(_item: dict, position: int, used: set[str]) -> str:
            if "future-unique-id" not in used:
                return "future-unique-id"
            return f"compatible-{position}"

        with patch.object(
            source_manager,
            "_compatible_instance_id",
            side_effect=compatible_id,
        ):
            resolved = source_manager._resolved_instance_ids(instances)

        self.assertEqual(resolved, ["compatible-0", "future-unique-id"])

    def test_create_validates_name_url_and_effective_api_key_without_leaking_env_key(self):
        sources = self._base_sources()
        sources["torznab"] = copy.deepcopy(DEFAULT_TORZNAB_SOURCE)
        sources["torznab_instances"] = []
        self._set_sources(sources)

        invalid_payloads = [
            {"type": "torznab", "base_url": "https://indexer.test", "api_key": "x"},
            {
                "type": "torznab",
                "name": "Indexer",
                "base_url": "ftp://indexer.test",
                "api_key": "x",
            },
            {"type": "torznab", "name": "Indexer", "base_url": "https://indexer.test"},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assert_error(400, source_manager.create_source, payload)
        self.replace_sources.assert_not_called()

        with patch.dict(os.environ, {"JAVHUB_TORZNAB_API_KEY": "env-secret"}, clear=False):
            snapshot = source_manager.create_source(
                {
                    "type": "torznab",
                    "kind": "prowlarr",
                    "name": "  Indexer  ",
                    "base_url": "https://indexer.test",
                }
            )
        saved = self.persisted_sources[-1]["torznab_instances"][0]
        self.assertEqual(saved["name"], "Indexer")
        self.assertFalse(saved.get("api_key"))
        public = snapshot["sources"][0]
        self.assertNotIn("api_key", public)
        self.assertTrue(public["api_key_configured"])

    def test_unknown_update_delete_and_type_report_structured_status_codes(self):
        self.assert_error(404, source_manager.update_source, "missing-id", {"name": "x"})
        self.assert_error(404, source_manager.delete_source, "missing-id")
        self.assert_error(400, source_manager.create_source, {"type": "unknown"})
        self.replace_sources.assert_not_called()

    def test_source_runtime_name_only_returns_searchable_enabled_sources(self):
        self.assertEqual(source_manager.source_runtime_name("jackett-id"), "Jackett")
        source_manager.config._config["sources"]["torznab_instances"][0]["enabled"] = False
        self.assertIsNone(source_manager.source_runtime_name("jackett-id"))
        self.assertIsNone(source_manager.source_runtime_name("missing-id"))

        sources = self._base_sources()
        sources["avdb"] = {"enabled": True, "sync_enabled": True}
        self._set_sources(sources)
        self.avdb_status.return_value = {"available": False}
        self.assertIsNone(source_manager.source_runtime_name("avdb"))
        self.avdb_status.return_value = {"available": True}
        self.assertEqual(source_manager.source_runtime_name("avdb"), "avdb")

    def test_whitespace_api_keys_are_not_configured_or_searchable(self):
        sources = self._base_sources()
        sources["torznab"]["api_key"] = "   "
        self._set_sources(sources)

        with patch.dict(os.environ, {"JAVHUB_TORZNAB_API_KEY": "   "}, clear=False):
            snapshot = source_manager.get_source_snapshot(avdb_status={"available": False})
            self.assertFalse(snapshot["sources"][0]["api_key_configured"])
            self.assertIsNone(
                source_manager.source_runtime_name(source_manager.LEGACY_TORZNAB_ID)
            )

    def test_refresh_runtime_reconfigures_avdb_job_only_while_scheduler_runs(self):
        with patch("sources.register_all_sources") as register, patch(
            "scheduler.tasks.scheduler", SimpleNamespace(running=True)
        ), patch("scheduler.tasks.configure_avdb_sync_job") as configure:
            self.real_refresh_runtime(avdb_changed=True)
        register.assert_called_once_with()
        configure.assert_called_once_with()

        with patch("sources.register_all_sources") as register, patch(
            "scheduler.tasks.scheduler", SimpleNamespace(running=False)
        ), patch("scheduler.tasks.configure_avdb_sync_job") as configure:
            self.real_refresh_runtime(avdb_changed=True)
        register.assert_called_once_with()
        configure.assert_not_called()

    def test_source_crud_holds_config_lock_across_read_modify_replace(self):
        original_sources_for_write = source_manager._sources_for_write
        crud_read_complete = threading.Event()
        release_crud = threading.Event()
        update_complete = threading.Event()
        errors: list[BaseException] = []

        def paused_sources_for_write() -> dict:
            sources = original_sources_for_write()
            crud_read_complete.set()
            if not release_crud.wait(timeout=2):
                raise TimeoutError("source CRUD coordination timed out")
            return sources

        def run_create() -> None:
            try:
                source_manager.create_source(
                    {
                        "type": "torznab",
                        "name": "Concurrent Indexer",
                        "base_url": "https://concurrent-indexer.test",
                        "api_key": "concurrent-secret",
                    }
                )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        def run_update() -> None:
            try:
                source_manager.config.update(
                    {"sources": {"external_marker": {"keep": True}}}
                )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)
            finally:
                update_complete.set()

        with patch.object(
            source_manager,
            "_sources_for_write",
            side_effect=paused_sources_for_write,
        ), patch.object(source_manager.config, "_write_config"):
            crud_thread = threading.Thread(target=run_create)
            crud_thread.start()
            self.assertTrue(crud_read_complete.wait(timeout=2))
            update_thread = threading.Thread(target=run_update)
            update_thread.start()
            update_finished_while_crud_paused = update_complete.wait(timeout=0.2)
            release_crud.set()
            crud_thread.join(timeout=2)
            update_thread.join(timeout=2)

        self.assertFalse(crud_thread.is_alive())
        self.assertFalse(update_thread.is_alive())
        self.assertFalse(update_finished_while_crud_paused)
        self.assertEqual(errors, [])
        saved_sources = source_manager.config._config["sources"]
        self.assertEqual(saved_sources["external_marker"], {"keep": True})
        self.assertIn(
            "Concurrent Indexer",
            [item["name"] for item in saved_sources["torznab_instances"]],
        )


class SourceRuntimeFilteringTest(unittest.TestCase):
    def test_management_metadata_never_reaches_torznab_constructor(self):
        from sources import register_all_sources
        from sources.registry import SourceRegistry
        from sources.torznab_source import TorznabSource

        cfg = object.__new__(Config)
        cfg._config = {
            "sources": {
                "torznab": copy.deepcopy(DEFAULT_TORZNAB_SOURCE),
                "torznab_instances": [
                    {
                        "id": "stable-id",
                        "kind": "jackett",
                        "type": "torznab",
                        "future_metadata": "must-not-leak",
                        "enabled": True,
                        "name": "Jackett",
                        "base_url": "https://jackett.test",
                        "api_key": "secret",
                    }
                ],
            }
        }

        runtime = cfg.enabled_torznab_configs
        self.assertEqual(
            set(runtime[0]),
            {
                "kind",
                "enabled",
                "name",
                "base_url",
                "api_key",
                "indexer",
                "categories",
                "limit",
                "timeout",
            },
        )
        self.assertEqual(runtime[0]["kind"], "jackett")
        with patch.object(SourceRegistry, "_sources", {}), patch.object(
            SourceRegistry, "_priority", []
        ), patch("sources.config", SimpleNamespace(enabled_torznab_configs=runtime)):
            register_all_sources()
            registered = SourceRegistry.get("Jackett")
            self.assertIsInstance(registered, TorznabSource)
            self.assertEqual(registered.kind, "jackett")


class ConfigAtomicWriteTest(unittest.TestCase):
    def test_replace_sources_deep_copies_and_atomically_replaces_temp_config(self):
        project_config = Path(__file__).resolve().parent.parent / "config.yaml"
        before = project_config.read_bytes() if project_config.exists() else None
        real_replace = os.replace
        real_safe_dump = yaml.safe_dump

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "isolated-config.yaml"
            cfg = object.__new__(Config)
            cfg._config_path = target
            cfg._config = {"server": {"port": 1234}, "sources": {"old": True}}
            replacement = {"torznab_instances": [{"id": "one", "api_key": "secret"}]}

            with patch("config.os.replace", wraps=real_replace) as replace_call, patch(
                "config.yaml.safe_dump", wraps=real_safe_dump
            ) as dump_call:
                cfg.replace_sources(replacement)

            replacement["torznab_instances"][0]["id"] = "mutated-after-save"
            self.assertEqual(
                cfg._config["sources"]["torznab_instances"][0]["id"],
                "one",
            )
            self.assertEqual(yaml.safe_load(target.read_text(encoding="utf-8")), cfg._config)
            replace_call.assert_called_once()
            source_path, destination_path = replace_call.call_args.args
            self.assertEqual(Path(destination_path), target)
            self.assertEqual(Path(source_path).parent, target.parent)
            self.assertFalse(Path(source_path).exists())
            self.assertEqual(
                dump_call.call_args.kwargs,
                {
                    "allow_unicode": True,
                    "default_flow_style": False,
                    "sort_keys": False,
                },
            )

        after = project_config.read_bytes() if project_config.exists() else None
        self.assertEqual(after, before)

    def test_update_reuses_atomic_write_boundary(self):
        cfg = object.__new__(Config)
        cfg._config = {"server": {"port": 1234}}
        with patch.object(cfg, "_write_config") as write_config:
            cfg.update({"server": {"port": 5678}})

        self.assertEqual(cfg._config["server"]["port"], 5678)
        write_config.assert_called_once_with(cfg._config)

    def test_failed_config_writes_leave_memory_disk_and_temp_files_unchanged(self):
        old_config = {
            "server": {"port": 1234},
            "sources": {"torznab_instances": [{"id": "old"}]},
        }
        cases = (
            ("replace_sources", "config.yaml.safe_dump"),
            ("replace_sources", "config.os.replace"),
            ("update", "config.yaml.safe_dump"),
            ("update", "config.os.replace"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "isolated-config.yaml"
            for operation, failure_point in cases:
                with self.subTest(operation=operation, failure_point=failure_point):
                    cfg = object.__new__(Config)
                    cfg._config_path = target
                    cfg._config = copy.deepcopy(old_config)
                    target.write_text(
                        yaml.safe_dump(old_config, sort_keys=False),
                        encoding="utf-8",
                    )

                    with patch(failure_point, side_effect=OSError("injected write failure")):
                        with self.assertRaisesRegex(OSError, "injected write failure"):
                            if operation == "replace_sources":
                                cfg.replace_sources(
                                    {"torznab_instances": [{"id": "new"}]}
                                )
                            else:
                                cfg.update({"server": {"port": 5678}})

                    self.assertEqual(cfg._config, old_config)
                    self.assertEqual(
                        yaml.safe_load(target.read_text(encoding="utf-8")),
                        old_config,
                    )
                    self.assertEqual(
                        list(target.parent.glob(f".{target.name}.*.tmp")),
                        [],
                    )

    def test_update_and_replace_sources_serialize_the_entire_read_modify_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cfg = object.__new__(Config)
            cfg._config_path = Path(temp_dir) / "isolated-config.yaml"
            cfg._config = {
                "server": {"port": 1234},
                "sources": {"torznab_instances": [{"id": "old"}]},
            }
            original_merge = cfg._merge_config
            merge_complete = threading.Event()
            release_update = threading.Event()
            replace_complete = threading.Event()
            errors: list[BaseException] = []

            def coordinated_merge(current: dict, incoming: dict) -> dict:
                merged = original_merge(current, incoming)
                if current.get("server") == {"port": 1234} and "server" in incoming:
                    merge_complete.set()
                    if not release_update.wait(timeout=2):
                        raise TimeoutError("update coordination timed out")
                return merged

            def run_update() -> None:
                try:
                    cfg.update({"server": {"port": 5678}})
                except BaseException as exc:  # pragma: no cover - asserted below
                    errors.append(exc)

            def run_replace() -> None:
                try:
                    cfg.replace_sources({"torznab_instances": [{"id": "new"}]})
                except BaseException as exc:  # pragma: no cover - asserted below
                    errors.append(exc)
                finally:
                    replace_complete.set()

            with patch.object(cfg, "_merge_config", side_effect=coordinated_merge):
                update_thread = threading.Thread(target=run_update)
                update_thread.start()
                self.assertTrue(merge_complete.wait(timeout=2))
                replace_thread = threading.Thread(target=run_replace)
                replace_thread.start()
                replace_complete.wait(timeout=0.2)
                release_update.set()
                update_thread.join(timeout=2)
                replace_thread.join(timeout=2)

            self.assertFalse(update_thread.is_alive())
            self.assertFalse(replace_thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(
                cfg._config["sources"]["torznab_instances"][0]["id"],
                "new",
            )


if __name__ == "__main__":
    unittest.main()
