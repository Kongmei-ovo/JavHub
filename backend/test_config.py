from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class SourceConfigTests(unittest.TestCase):
    def test_numeric_clamp_helpers_normalize_invalid_and_out_of_range_values(self):
        from config import Config

        self.assertEqual(Config._clamp_int("12", 5, 1, 10), 10)
        self.assertEqual(Config._clamp_int("bad", 5, 1, 10), 5)
        self.assertEqual(Config._clamp_int("5000", 5, 1), 5000)
        self.assertEqual(Config._clamp_float("1.5", 0.5, 0.0, 1.0), 1.0)
        self.assertEqual(Config._clamp_float("bad", 0.5, 0.0, 1.0), 0.5)

    def test_numeric_config_properties_preserve_clamp_semantics(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {
            "automation": {
                "auto_process_interval_minutes": 0,
                "max_auto_downloads_per_run": -1,
                "max_auto_downloads_per_24h": "bad",
            },
            "actor_mapping": {
                "candidate_per_actor": 99,
                "candidate_min_confidence": "-1",
                "auto_confirm_confidence": "bad",
                "auto_confirm_gap": "1.5",
            },
            "translation": {
                "batch_concurrency": 0,
                "batch_size": "bad",
                "batch_char_limit": 1,
                "source_page_size": 5000,
                "scan_pages_per_batch": -2,
            },
        }

        self.assertEqual(cfg.automation_auto_process_interval_minutes, 0)
        self.assertEqual(cfg.automation_max_auto_downloads_per_run, 0)
        self.assertEqual(cfg.automation_max_auto_downloads_per_24h, 100)
        self.assertEqual(cfg.actor_mapping_candidate_per_actor, 10)
        self.assertEqual(cfg.actor_mapping_candidate_min_confidence, 0.0)
        self.assertEqual(cfg.actor_mapping_auto_confirm_confidence, 0.98)
        self.assertEqual(cfg.actor_mapping_auto_confirm_gap, 1.0)
        self.assertEqual(cfg.translation_batch_concurrency, 32)
        self.assertEqual(cfg.translation_batch_size, 200)
        self.assertEqual(cfg.translation_batch_char_limit, 500)
        self.assertEqual(cfg.translation_source_page_size, 1000)
        self.assertEqual(cfg.translation_scan_pages_per_batch, 1)

    def test_variant_index_rebuild_hour_parsing(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {"scheduler": {}}
        self.assertEqual(cfg.scheduler_variant_index_rebuild_hour, 4)
        cfg._config = {"scheduler": {"variant_index_rebuild_hour": 6}}
        self.assertEqual(cfg.scheduler_variant_index_rebuild_hour, 6)
        cfg._config = {"scheduler": {"variant_index_rebuild_hour": None}}
        self.assertIsNone(cfg.scheduler_variant_index_rebuild_hour)
        cfg._config = {"scheduler": {"variant_index_rebuild_hour": -1}}
        self.assertIsNone(cfg.scheduler_variant_index_rebuild_hour)
        cfg._config = {"scheduler": {"variant_index_rebuild_hour": "bad"}}
        self.assertEqual(cfg.scheduler_variant_index_rebuild_hour, 4)

    def test_javhub_database_uses_dedicated_env_without_polluting_javinfo_import(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {}

        env = {
            "DB_HOST": "metadata-postgres",
            "DB_PORT": "15432",
            "DB_USER": "javinfo-user",
            "DB_PASSWORD": "javinfo-secret",
            "DB_NAME": "r18",
            "JAVHUB_DB_HOST": "state-postgres",
            "JAVHUB_DB_PORT": "25432",
            "JAVHUB_DB_USER": "javhub-user",
            "JAVHUB_DB_PASSWORD": "javhub-secret",
            "JAVHUB_DB_NAME": "javhub",
        }

        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(cfg.javhub_database["host"], "state-postgres")
            self.assertEqual(cfg.javhub_database["port"], 25432)
            self.assertEqual(cfg.javhub_database["user"], "javhub-user")
            self.assertEqual(cfg.javhub_database["password"], "javhub-secret")
            self.assertEqual(cfg.javhub_database["database"], "javhub")

            self.assertEqual(cfg.javinfo_import_db["host"], "metadata-postgres")
            self.assertEqual(cfg.javinfo_import_db["database"], "r18")
            self.assertEqual(cfg.javinfo_import_db["user"], "javinfo-user")

    def test_sanitizer_removes_nested_source_api_keys(self):
        from routers.config import _sanitize_config

        sanitized = _sanitize_config(
            {
                "sources": {
                    "torznab": {
                        "enabled": True,
                        "base_url": "http://prowlarr:9696",
                        "api_key": "secret",
                    },
                    "torznab_instances": [
                        {
                            "name": "jackett",
                            "enabled": True,
                            "base_url": "http://jackett:9117",
                            "api_key": "other-secret",
                        }
                    ],
                }
            }
        )

        self.assertNotIn("api_key", sanitized["sources"]["torznab"])
        self.assertNotIn("api_key", sanitized["sources"]["torznab_instances"][0])
        self.assertEqual(sanitized["sources"]["torznab"]["base_url"], "http://prowlarr:9696")

    def test_torznab_api_key_uses_env_when_config_is_absent(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {
            "sources": {
                "torznab": {
                    "enabled": True,
                    "base_url": "http://prowlarr:9696",
                },
                "torznab_instances": [
                    {
                        "enabled": True,
                        "base_url": "http://jackett:9117",
                    }
                ],
            }
        }

        with patch.dict(os.environ, {"JAVHUB_TORZNAB_API_KEY": "env-secret"}, clear=False):
            self.assertEqual(cfg.enabled_torznab_configs[0]["api_key"], "env-secret")
            self.assertEqual(cfg.enabled_torznab_configs[1]["api_key"], "env-secret")

        cfg._config["sources"]["torznab"]["api_key"] = "config-secret"
        with patch.dict(os.environ, {"JAVHUB_TORZNAB_API_KEY": "env-secret"}, clear=False):
            self.assertEqual(cfg.enabled_torznab_configs[0]["api_key"], "config-secret")
            self.assertEqual(cfg.enabled_torznab_configs[1]["api_key"], "env-secret")

    def test_torznab_configs_normalize_limits_timeouts_and_names(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {
            "sources": {
                "torznab": {
                    "enabled": True,
                    "name": "",
                    "base_url": "http://prowlarr:9696",
                    "limit": 0,
                    "timeout": 999,
                },
                "torznab_instances": [
                    {
                        "enabled": False,
                        "name": "backup",
                        "base_url": "http://jackett:9117",
                        "limit": 250,
                        "timeout": "bad",
                        "indexer": "",
                    }
                ],
            }
        }

        all_configs = cfg.source_torznab_configs
        self.assertEqual(len(all_configs), 2)
        self.assertEqual(all_configs[0]["name"], "torznab-1")
        self.assertEqual(all_configs[0]["limit"], 1)
        self.assertEqual(all_configs[0]["timeout"], 60)
        self.assertEqual(all_configs[0]["indexer"], "all")
        self.assertEqual(all_configs[1]["name"], "backup")
        self.assertEqual(all_configs[1]["limit"], 100)
        self.assertEqual(all_configs[1]["timeout"], 15)
        self.assertEqual(all_configs[1]["indexer"], "all")
        self.assertEqual([item["name"] for item in cfg.enabled_torznab_configs], ["torznab-1"])

    def test_sources_defaults_when_sources_config_is_not_a_mapping(self):
        from config import Config

        cfg = Config.__new__(Config)
        cfg._config = {"sources": "bad"}

        self.assertEqual(cfg.sources["torznab"]["enabled"], False)
        self.assertEqual(cfg.source_torznab_configs[0]["name"], "torznab")
