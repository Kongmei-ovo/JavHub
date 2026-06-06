from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from test_support.client import create_router_test_client
from test_support.postgres import TempPostgresMixin


class SourceAttemptPersistenceTest(TempPostgresMixin, unittest.TestCase):
    def test_records_queries_and_summarizes_recent_attempts(self):
        from database.source_attempt import list_recent_source_attempts, record_source_attempt, source_health_summary

        now = datetime.now(timezone.utc)
        record_source_attempt(
            source="m3u8",
            keyword="MIDE-900",
            ok=True,
            duration_ms=10,
            result_count=2,
            created_at=now - timedelta(minutes=4),
            prune_chance=0,
        )
        record_source_attempt(
            source="m3u8",
            keyword="MIDE-900",
            ok=True,
            duration_ms=20,
            result_count=1,
            created_at=now - timedelta(minutes=3),
            prune_chance=0,
        )
        record_source_attempt(
            source="m3u8",
            keyword="MIDE-900",
            ok=False,
            duration_ms=30,
            result_count=0,
            error="RuntimeError: timeout",
            created_at=now - timedelta(minutes=2),
            prune_chance=0,
        )
        record_source_attempt(
            source="torznab",
            keyword="MIDE-900",
            ok=True,
            duration_ms=100,
            result_count=3,
            created_at=now - timedelta(minutes=1),
            prune_chance=0,
        )
        record_source_attempt(
            source="stale",
            keyword="MIDE-900",
            ok=False,
            duration_ms=999,
            result_count=0,
            error="too old",
            created_at=now - timedelta(hours=2),
            prune_chance=0,
        )

        recent = list_recent_source_attempts(limit=2)
        self.assertEqual([row["source"] for row in recent], ["torznab", "m3u8"])
        self.assertEqual(recent[0]["keyword"], "MIDE-900")
        self.assertTrue(recent[0]["ok"])

        summary = source_health_summary(window_minutes=60)

        by_name = {row["name"]: row for row in summary}
        self.assertEqual(set(by_name), {"m3u8", "torznab"})
        self.assertEqual(by_name["m3u8"]["total"], 3)
        self.assertEqual(by_name["m3u8"]["ok"], 2)
        self.assertAlmostEqual(by_name["m3u8"]["ok_ratio"], 2 / 3)
        self.assertEqual(by_name["m3u8"]["p50_ms"], 20)
        self.assertGreater(by_name["m3u8"]["p95_ms"], 20)
        self.assertEqual(by_name["m3u8"]["last_error"], "RuntimeError: timeout")
        self.assertEqual(by_name["torznab"]["total"], 1)
        self.assertEqual(by_name["torznab"]["ok"], 1)
        self.assertEqual(by_name["torznab"]["ok_ratio"], 1)
        self.assertEqual(by_name["torznab"]["p50_ms"], 100)
        self.assertEqual(by_name["torznab"]["p95_ms"], 100)
        self.assertEqual(by_name["torznab"]["last_error"], "")

    def test_retention_prunes_oldest_rows_when_chance_triggers(self):
        from database.source_attempt import list_recent_source_attempts, record_source_attempt

        now = datetime.now(timezone.utc)
        for index in range(5):
            record_source_attempt(
                source="m3u8",
                keyword=f"kw-{index}",
                ok=True,
                duration_ms=index,
                result_count=index,
                created_at=now + timedelta(seconds=index),
                retention_limit=3,
                prune_chance=1,
            )

        recent = list_recent_source_attempts(limit=10)

        self.assertEqual([row["keyword"] for row in recent], ["kw-4", "kw-3", "kw-2"])

    def test_health_route_returns_source_attempt_summary(self):
        from database.source_attempt import record_source_attempt
        from routers.source_health import router

        record_source_attempt(
            source="m3u8",
            keyword="ABP-588",
            ok=False,
            duration_ms=42,
            result_count=0,
            error="ValueError: bad upstream response",
            prune_chance=0,
        )

        response = create_router_test_client(router).get("/api/v1/sources/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "name": "m3u8",
                    "total": 1,
                    "ok": 0,
                    "ok_ratio": 0,
                    "p50_ms": 42,
                    "p95_ms": 42,
                    "last_error": "ValueError: bad upstream response",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
