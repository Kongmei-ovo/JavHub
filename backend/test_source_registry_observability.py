from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch


class SuccessfulSource:
    def __init__(self, name: str, rows: list[dict]):
        self.name = name
        self.rows = rows

    async def search(self, keyword: str) -> list[dict]:
        return self.rows


class FailingSource:
    def __init__(self, name: str, error: Exception):
        self.name = name
        self.error = error

    async def search(self, keyword: str) -> list[dict]:
        raise self.error


class SourceRegistryObservabilityTest(unittest.IsolatedAsyncioTestCase):
    async def test_register_all_sources_keeps_only_implemented_sources(self):
        import sources
        from sources.m3u8_source import M3U8Source
        from sources.registry import SourceRegistry
        from sources.torznab_source import TorznabSource

        configs = [
            {
                "enabled": True,
                "name": "primary-indexer",
                "base_url": "http://prowlarr.test",
                "api_key": "secret",
                "indexer": "all",
                "categories": "",
                "limit": 20,
                "timeout": 15,
            }
        ]

        with patch.object(SourceRegistry, "_sources", {}), \
             patch.object(SourceRegistry, "_priority", []), \
             patch.object(sources, "config", SimpleNamespace(enabled_torznab_configs=configs)):
            sources.register_all_sources()

            self.assertEqual(SourceRegistry.priority(), ["m3u8", "primary-indexer"])
            self.assertIsInstance(SourceRegistry.get("m3u8"), M3U8Source)
            self.assertIsInstance(SourceRegistry.get("primary-indexer"), TorznabSource)
            self.assertFalse(hasattr(sources, "JavBusSource"))
            self.assertFalse(hasattr(sources, "JavDBSource"))
            self.assertFalse(hasattr(sources, "JavLibSource"))

    async def test_search_all_records_success_and_failure_attempts(self):
        from sources.registry import SourceRegistry

        SourceRegistry.clear_attempts()

        working = SuccessfulSource(
            "working",
            [
                {"title": "SIVR-438 1080p", "magnet": "magnet:?xt=urn:btih:111"},
                {"title": "SIVR-438 720p", "source": "explicit-source"},
            ],
        )
        broken = FailingSource("broken", RuntimeError("indexer timeout"))

        with patch.object(SourceRegistry, "_sources", {"broken": broken, "working": working}), \
             patch.object(SourceRegistry, "_priority", ["broken", "working"]), \
             patch("database.source_attempt.record_source_attempt") as record_source_attempt:
            results = await SourceRegistry.search_all("SIVR-438")

        self.assertEqual([row["title"] for row in results], ["SIVR-438 1080p", "SIVR-438 720p"])
        self.assertEqual(results[0]["source"], "working")
        self.assertEqual(results[1]["source"], "explicit-source")

        attempts = SourceRegistry.recent_attempts(limit=10)
        self.assertEqual(len(attempts), 2)

        failed_attempt, successful_attempt = attempts
        self.assertEqual(failed_attempt["source"], "broken")
        self.assertEqual(failed_attempt["keyword"], "SIVR-438")
        self.assertFalse(failed_attempt["ok"])
        self.assertEqual(failed_attempt["result_count"], 0)
        self.assertIn("indexer timeout", failed_attempt["error"])
        self.assertGreaterEqual(failed_attempt["duration_ms"], 0)
        self.assertTrue(failed_attempt["timestamp"])

        self.assertEqual(successful_attempt["source"], "working")
        self.assertEqual(successful_attempt["keyword"], "SIVR-438")
        self.assertTrue(successful_attempt["ok"])
        self.assertEqual(successful_attempt["result_count"], 2)
        self.assertEqual(successful_attempt["error"], "")
        self.assertGreaterEqual(successful_attempt["duration_ms"], 0)
        self.assertTrue(successful_attempt["timestamp"])

        self.assertEqual(record_source_attempt.call_count, 2)
        first_call, second_call = record_source_attempt.call_args_list
        self.assertEqual(first_call.kwargs["source"], "broken")
        self.assertEqual(first_call.kwargs["keyword"], "SIVR-438")
        self.assertFalse(first_call.kwargs["ok"])
        self.assertEqual(first_call.kwargs["result_count"], 0)
        self.assertIn("indexer timeout", first_call.kwargs["error"])
        self.assertGreaterEqual(first_call.kwargs["duration_ms"], 0)
        self.assertEqual(second_call.kwargs["source"], "working")
        self.assertEqual(second_call.kwargs["keyword"], "SIVR-438")
        self.assertTrue(second_call.kwargs["ok"])
        self.assertEqual(second_call.kwargs["result_count"], 2)
        self.assertEqual(second_call.kwargs["error"], "")
        self.assertGreaterEqual(second_call.kwargs["duration_ms"], 0)

    async def test_recent_attempts_are_bounded_and_limitable(self):
        from sources.registry import SourceRegistry

        SourceRegistry.clear_attempts()

        sources = {}
        priority = []
        for index in range(205):
            name = f"source-{index}"
            sources[name] = SuccessfulSource(name, [{"title": f"result-{index}"}])
            priority.append(name)

        with patch.object(SourceRegistry, "_sources", sources), \
             patch.object(SourceRegistry, "_priority", priority), \
             patch("database.source_attempt.record_source_attempt"):
            await SourceRegistry.search_all("ABP-588")

        attempts = SourceRegistry.recent_attempts(limit=500)
        self.assertLessEqual(len(attempts), 200)
        self.assertEqual(attempts[0]["source"], "source-5")
        self.assertEqual(attempts[-1]["source"], "source-204")

        latest_three = SourceRegistry.recent_attempts(limit=3)
        self.assertEqual([attempt["source"] for attempt in latest_three], ["source-202", "source-203", "source-204"])
