from __future__ import annotations

import asyncio
import unittest

from test_support.postgres import TempPostgresMixin


class DataQualityHistoryTest(TempPostgresMixin, unittest.TestCase):
    def test_overview_upserts_one_snapshot_per_day_with_issue_type_counts(self):
        from database import get_db
        from services.data_quality import build_data_quality_overview

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("MIDE-900", "MIDE-900", "待补磁力", 901, "Actor", "https://example.com/cover.jpg", "subscription", "test", "candidate", ""),
            )

        first = build_data_quality_overview(limit=20)
        second = build_data_quality_overview(limit=20)

        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM data_quality_snapshots")
            count_row = cursor.fetchone()
            cursor.execute(
                """
                SELECT summary, issues_by_type
                FROM data_quality_snapshots
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """
            )
            snapshot_row = cursor.fetchone()

        self.assertEqual(count_row["cnt"], 1)
        self.assertEqual(snapshot_row["summary"]["total_issues"], second["summary"]["total_issues"])
        self.assertEqual(snapshot_row["issues_by_type"]["missing_download_link"]["count"], 1)
        self.assertEqual(snapshot_row["issues_by_type"]["missing_download_link"]["severity"], "high")

    def test_history_route_returns_recent_daily_series(self):
        from database import get_db
        from database.data_quality_history import ensure_data_quality_history_schema
        from routers import data_quality

        ensure_data_quality_history_schema()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO data_quality_snapshots (captured_at, summary, issues_by_type)
                VALUES
                    (
                        CURRENT_TIMESTAMP - INTERVAL '2 days',
                        ?::jsonb,
                        ?::jsonb
                    ),
                    (
                        CURRENT_TIMESTAMP - INTERVAL '1 day',
                        ?::jsonb,
                        ?::jsonb
                    ),
                    (
                        CURRENT_TIMESTAMP,
                        ?::jsonb,
                        ?::jsonb
                    )
                """,
                (
                    '{"total_issues": 1, "high": 1}',
                    '{"missing_field": {"count": 3, "severity": "high"}}',
                    '{"total_issues": 2, "high": 1, "medium": 1}',
                    '{"missing_field": {"count": 2, "severity": "medium"}, "dead_link": {"count": 1, "severity": "medium"}}',
                    '{"total_issues": 1, "critical": 1}',
                    '{"duplicate_data": {"count": 4, "severity": "critical"}}',
                ),
            )

        result = asyncio.run(data_quality.data_quality_history(days=2))

        self.assertEqual(result["days"], 2)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(
            [item["summary"]["total_issues"] for item in result["items"]],
            [2, 1],
        )
        self.assertEqual(
            result["items"][0]["issues_by_type"]["dead_link"],
            {"count": 1, "severity": "medium"},
        )
        self.assertEqual(
            result["items"][1]["issues_by_type"]["duplicate_data"],
            {"count": 4, "severity": "critical"},
        )


if __name__ == "__main__":
    unittest.main()
