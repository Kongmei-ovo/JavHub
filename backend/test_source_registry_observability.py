from __future__ import annotations

import unittest
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
             patch.object(SourceRegistry, "_priority", ["broken", "working"]):
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
             patch.object(SourceRegistry, "_priority", priority):
            await SourceRegistry.search_all("ABP-588")

        attempts = SourceRegistry.recent_attempts(limit=500)
        self.assertLessEqual(len(attempts), 200)
        self.assertEqual(attempts[0]["source"], "source-5")
        self.assertEqual(attempts[-1]["source"], "source-204")

        latest_three = SourceRegistry.recent_attempts(limit=3)
        self.assertEqual([attempt["source"] for attempt in latest_three], ["source-202", "source-203", "source-204"])
