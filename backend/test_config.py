from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class SourceConfigTests(unittest.TestCase):
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
