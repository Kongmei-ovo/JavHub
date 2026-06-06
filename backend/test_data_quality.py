from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.postgres import TempPostgresMixin


class DataQualityOverviewTest(TempPostgresMixin, unittest.TestCase):
    def test_overview_detects_and_prioritizes_library_data_quality_issues(self):
        from database import (
            create_snapshot_key,
            get_db,
            save_emby_actors_snapshot,
            save_emvy_snapshot,
            upsert_inventory_video,
        )
        from services.data_quality import build_data_quality_overview

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [
            {"actress_id": 901, "actress_name": "Emby Actor", "video_count": 3},
        ])
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-1", "ABP-123 Title", "ABP-123.mp4")
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-2", "ABP-123 Title (1)", "ABP-123-copy.mp4")
        save_emvy_snapshot(snapshot_key, 901, "Emby Actor", "item-3", "", "")

        upsert_inventory_video("MIAA-001", "emby-miaa", 901, "库存标题", "2024-01-01", "")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO missing_videos (content_id, actress_id, title, release_date, jacket_thumb_url, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("MIAA-001", 901, "缺失标题", "2023-01-01", "https://example.com/noimage.jpg", "javinfo"),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("bad code", "bad code", "", 901, "Emby Actor", "ftp://covers.invalid/bad.jpg", "inventory", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("JUL652", "JUL-652", "紧凑番号", 901, "Emby Actor", "https://example.com/jul652.jpg", "inventory", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("DANUHD1", "DANUHD-1", "一位数字番号", 901, "Emby Actor", "https://example.com/danuhd1.jpg", "inventory", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("3DSVR609", "3DSVR-609", "数字前缀番号", 901, "Emby Actor", "https://example.com/3dsvr609.jpg", "inventory", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("SSIS-777", "SSIS-777", "缺磁力候选", 901, "Emby Actor", "https://example.com/ssis777.jpg", "supplement", "test", "candidate", ""),
            )

        result = build_data_quality_overview(limit=20)

        issue_types = [issue["type"] for issue in result["issues"]]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["snapshot_key"], snapshot_key)
        self.assertEqual(result["summary"]["total_issues"], len(result["issues"]))
        self.assertIn("duplicate_data", issue_types)
        self.assertIn("missing_field", issue_types)
        self.assertIn("invalid_field", issue_types)
        self.assertIn("low_quality_cover", issue_types)
        self.assertIn("dead_link", issue_types)
        self.assertIn("inconsistent_metadata", issue_types)
        self.assertIn("missing_download_link", issue_types)
        invalid_issue = next(issue for issue in result["issues"] if issue["type"] == "invalid_field")
        self.assertEqual(invalid_issue["count"], 1)
        self.assertEqual(invalid_issue["samples"][0]["value"], "bad code")
        self.assertEqual(result["issues"][0]["type"], "duplicate_data")
        self.assertGreater(result["issues"][0]["score"], result["issues"][-1]["score"])
        self.assertTrue(result["issues"][0]["action"]["route"].startswith("/library-organize"))
        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["action"]["route"], "/supplement?tab=movies&quality=missing_cover")
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")
        self.assertEqual(link_issue["count"], 5)
        self.assertEqual(link_issue["severity"], "high")
        self.assertEqual(link_issue["action"]["route"], "/downloads?tab=candidates&status=candidate&needs_magnet=1")
        self.assertEqual(link_issue["repair_progress"], {
            "state": "blocked",
            "queued": 5,
            "ready": 0,
            "label": "候选修复 5 待补磁力 · 0 可批准",
            "action": {
                "label": "批量补当前磁力",
                "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1",
            },
            "provider_label": "来源 inventory 4 · supplement 1",
            "provider_actions": [
                {
                    "provider": "inventory",
                    "label": "查看 inventory 待补磁力",
                    "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&source=inventory",
                },
                {
                    "provider": "supplement",
                    "label": "查看 supplement 待补磁力",
                    "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&source=supplement",
                },
            ],
        })
        self.assertLessEqual(len(result["issues"]), 20)

    def test_low_quality_cover_issue_exposes_repair_progress_when_supplied(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-001", "emby-miaa", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "available": True,
                    "queued": 5,
                    "running": 1,
                    "failed": 2,
                    "failed_reasons": [
                        {"label": "来源暂不可用", "count": 3},
                        {"label": "低置信匹配", "count": 2},
                    ],
                    "provider_failures": [
                        {"provider": "javlibrary", "count": 3, "route_source": "all"},
                        {"provider": "fanza", "count": 2},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["repair_progress"], {
            "state": "running",
            "queued": 5,
            "running": 1,
            "failed": 2,
            "label": "补全修复 1 运行 · 5 排队 · 2 失败",
            "action": {
                "label": "查看失败补全任务",
                "route": "/supplement?tab=jobs&status=failed",
            },
            "failed_reasons": [
                {"label": "来源暂不可用", "count": 3},
                {"label": "低置信匹配", "count": 2},
            ],
            "reason_label": "失败原因 来源暂不可用 3 · 低置信匹配 2",
            "reason_action": {
                "label": "检查补全来源",
                "route": "/supplement?tab=sources",
            },
            "provider_failures": [
                {"provider": "javlibrary", "count": 3, "route_source": "all"},
                {"provider": "fanza", "count": 2},
            ],
            "provider_label": "来源 javlibrary 3 · fanza 2",
            "provider_actions": [
                {
                    "provider": "javlibrary",
                    "label": "查看含 javlibrary 的失败",
                    "route": "/supplement?tab=jobs&status=failed&source=all&error_provider=javlibrary",
                },
                {
                    "provider": "fanza",
                    "label": "查看 fanza 失败",
                    "route": "/supplement?tab=jobs&status=failed&source=fanza",
                },
            ],
        })

    def test_low_quality_cover_provider_label_marks_folded_sources(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-002", "emby-miaa-2", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 6,
                    "provider_failures": [
                        {"provider": "avbase", "count": 5, "route_source": "all"},
                        {"provider": "fanza", "count": 5, "route_source": "all"},
                        {"provider": "fc2", "count": 5, "route_source": "all"},
                        {"provider": "jav321", "count": 5, "route_source": "all"},
                        {"provider": "javbus", "count": 5, "route_source": "all"},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["repair_progress"]["provider_label"], "来源 avbase 5 · fanza 5 · fc2 5 · jav321 5 · 另 1 来源")
        self.assertEqual(cover_issue["repair_progress"]["provider_actions"][0]["label"], "查看含 avbase 的失败")
        self.assertEqual(
            cover_issue["repair_progress"]["provider_actions"][0]["route"],
            "/supplement?tab=jobs&status=failed&source=all&error_provider=avbase",
        )

    def test_low_quality_cover_repair_failures_raise_priority(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-003", "emby-miaa-3", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 42,
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["severity"], "high")
        self.assertGreaterEqual(cover_issue["score"], 82)
        self.assertEqual(cover_issue["priority_reason"], "42 个补全任务失败，先处理补全来源再批量补封面。")

    def test_overview_route_and_operations_route_expose_same_data_quality_summary(self):
        from routers import data_quality, operations

        overview = {
            "status": "ok",
            "snapshot_key": "snap-1",
            "summary": {"total_issues": 2, "high": 1, "medium": 1, "low": 0, "critical": 0},
            "issues": [{"id": "duplicate:ABP-123", "type": "duplicate_data", "score": 90}],
        }

        with patch.object(data_quality, "get_supplement_repair_progress", AsyncMock(return_value={})) as progress, \
            patch.object(data_quality, "build_data_quality_overview", Mock(return_value=overview)) as audit:
            result = asyncio.run(data_quality.data_quality_overview(limit=5))

        progress.assert_awaited_once_with()
        audit.assert_called_once_with(limit=5)
        self.assertEqual(result, overview)

        with patch.object(operations, "config", Mock(
                automation={"enabled": True},
                actor_mapping={"enabled": False},
            )), \
            patch.object(operations, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(operations, "count_snapshot_actors", Mock(return_value=1)), \
            patch.object(operations, "download_candidate_stats", Mock(return_value={"total": 0})), \
            patch.object(operations, "get_inventory_jobs", Mock(return_value=[])), \
            patch.object(operations, "missing_videos_summary", Mock(return_value={"total": 0, "top_actresses": []})), \
            patch.object(operations, "variant_group_stats", Mock(return_value={"group_count": 0})), \
            patch.object(operations, "mapping_summary_for_snapshot", Mock(return_value={"mapped": 0})), \
            patch.object(operations, "list_candidate_process_runs", Mock(return_value=[])), \
            patch.object(operations, "_candidate_schedule_state", Mock(return_value={"effective_enabled": False})), \
            patch.object(operations, "build_data_quality_overview", Mock(return_value=overview)) as audit, \
            patch("modules.info_client.get_info_client", Mock(side_effect=RuntimeError("javinfo down"))):
            result = asyncio.run(operations.operations_overview(cache_control="0"))

        audit.assert_called_once_with(limit=8)
        self.assertEqual(result["data_quality"], overview)

    def test_data_quality_route_uses_supplement_repair_progress(self):
        from routers import data_quality

        overview = {
            "status": "ok",
            "snapshot_key": "snap-1",
            "summary": {"total_issues": 1, "high": 1, "medium": 0, "low": 0, "critical": 0},
            "issues": [{"id": "low_quality_cover:MIAA-001", "type": "low_quality_cover", "score": 89}],
        }
        repair_progress = {"low_quality_cover": {"failed": 42}}

        with patch.object(data_quality, "get_supplement_repair_progress", AsyncMock(return_value=repair_progress), create=True) as progress, \
            patch.object(data_quality, "build_data_quality_overview", Mock(return_value=overview)) as audit:
            result = asyncio.run(data_quality.data_quality_overview(limit=5))

        progress.assert_awaited_once_with()
        audit.assert_called_once_with(limit=5, repair_progress=repair_progress)
        self.assertEqual(result, overview)


if __name__ == "__main__":
    unittest.main()
