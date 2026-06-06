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

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
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
            "policy": "manual",
            "label": "候选修复 5 待补磁力 · 0 可批准",
            "action": {
                "label": "批量补当前磁力",
                "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1",
            },
            "event_label": "最近动作 未处理 5",
            "event_actions": [
                {
                    "label": "查看未处理候选",
                    "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&latest_event_action=without_event",
                },
            ],
            "reason_label": "未执行候选处理 · 先预演或批量补磁力",
            "reason_action": {
                "label": "查看未处理候选",
                "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&latest_event_action=without_event",
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
            "reason_actions": [
                {
                    "label": "查看低置信匹配失败",
                    "route": "/supplement?tab=jobs&status=failed&error_reason=low_confidence",
                },
            ],
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

    def test_low_quality_cover_issue_links_local_candidate_sources(self):
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
                ("SUP-001", "SUP-001", "补全缺封面", 901, "Actor", "", "supplement", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("SUB-001", "SUB-001", "订阅缺封面", 901, "Actor", "https://example.com/noimage.jpg", "subscription", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("OK-001", "OK-001", "有封面", 901, "Actor", "https://example.com/ok.jpg", "subscription", "test", "candidate", ""),
            )

        result = build_data_quality_overview(limit=20)
        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")

        self.assertEqual(cover_issue["repair_progress"]["local_label"], "本地缺封面 候选 2")
        self.assertEqual(
            sorted(cover_issue["repair_progress"]["local_actions"], key=lambda item: item["label"]),
            [
                {
                    "label": "查看 subscription 缺封面候选",
                    "route": "/downloads?tab=candidates&status=candidate&source=subscription&missing_cover=1",
                },
                {
                    "label": "查看 supplement 缺封面候选",
                    "route": "/downloads?tab=candidates&status=candidate&source=supplement&missing_cover=1",
                },
            ],
        )

    def test_missing_download_link_issue_exposes_candidate_process_history(self):
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
                ("MIDE-777", "MIDE-777", "待补磁力 A", 901, "Actor", "https://example.com/a.jpg", "subscription", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("MIDE-778", "MIDE-778", "待补磁力 B", 901, "Actor", "https://example.com/b.jpg", "supplement", "test", "candidate", ""),
            )
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("MIDE-779", "MIDE-779", "可批准", 901, "Actor", "https://example.com/c.jpg", "subscription", "test", "candidate", "magnet:?xt=urn:btih:abc"),
            )
            cursor.execute(
                """
                INSERT INTO candidate_process_runs (
                    trigger_source, policy, status, filters_json, result_json,
                    total, sent, failed, skipped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("manual", "auto", "completed", "{}", "{}", 2, 0, 1, 1),
            )

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
            result = build_data_quality_overview(limit=20)
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")

        self.assertEqual(link_issue["repair_progress"]["label"], "候选修复 2 待补磁力 · 1 可批准")
        self.assertEqual(link_issue["repair_progress"]["reason_label"], "最近处理 下发 0 · 失败 1 · 跳过 1")
        self.assertEqual(link_issue["repair_progress"]["reason_action"], {
            "label": "查看候选处理记录",
            "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1",
        })
        self.assertEqual(link_issue["repair_progress"]["last_run"], {
            "policy": "auto",
            "total": 2,
            "sent": 0,
            "failed": 1,
            "skipped": 1,
        })

    def test_missing_download_link_issue_marks_manual_policy_as_repair_blocker(self):
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
                ("MIDE-780", "MIDE-780", "人工策略待补磁力", 901, "Actor", "https://example.com/manual.jpg", "subscription", "test", "candidate", ""),
            )

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
            result = build_data_quality_overview(limit=20)
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")

        self.assertEqual(link_issue["repair_progress"]["reason_label"], "未执行候选处理 · 先预演或批量补磁力")
        self.assertEqual(link_issue["repair_progress"]["reason_action"], {
            "label": "查看未处理候选",
            "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&latest_event_action=without_event",
        })
        self.assertEqual(link_issue["repair_progress"]["event_label"], "最近动作 未处理 1")
        self.assertEqual(link_issue["repair_progress"]["event_actions"], [
            {
                "label": "查看未处理候选",
                "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&latest_event_action=without_event",
            },
        ])
        self.assertEqual(link_issue["repair_progress"]["policy"], "manual")

    def test_missing_download_link_issue_explains_candidate_preview_blocker(self):
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
                ("MIDE-781", "MIDE-781", "预演待补磁力", 901, "Actor", "https://example.com/preview.jpg", "supplement", "test", "candidate", ""),
            )

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
            result = build_data_quality_overview(
                limit=20,
                repair_progress={
                    "missing_download_link": {
                        "candidate_preview": {
                            "dry_run": True,
                            "policy": "manual",
                            "total": 50,
                            "counts": {"manual_required": 50},
                            "limits": {"per_run": 20, "per_24h": 100, "remaining": 20},
                        },
                    },
                },
            )
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")

        self.assertEqual(link_issue["repair_progress"]["preview"], {
            "policy": "manual",
            "total": 50,
            "manual_required": 50,
            "would_enrich_magnet": 0,
            "would_send": 0,
            "would_skip_limit": 0,
        })
        self.assertEqual(link_issue["repair_progress"]["reason_label"], "预演 50 个 · 50 个需人工批准")
        self.assertEqual(link_issue["repair_progress"]["reason_action"], {
            "label": "调整候选自动化",
            "route": "/settings?tab=automation",
        })

    def test_missing_download_link_issue_prioritizes_safe_magnet_repair_preview(self):
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
                ("JUL-652", "JUL-652", "待补磁力", 901, "Actor", "https://example.com/jul652.jpg", "supplement", "test", "candidate", ""),
            )

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
            result = build_data_quality_overview(
                limit=20,
                repair_progress={
                    "missing_download_link": {
                        "candidate_preview": {
                            "dry_run": True,
                            "policy": "rules",
                            "total": 50,
                            "counts": {"would_enrich_magnet": 50},
                            "limits": {"per_run": 20, "per_24h": 100, "remaining": 20},
                        },
                    },
                },
            )
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")

        self.assertEqual(link_issue["repair_progress"]["reason_label"], "预演 50 个 · 50 个可尝试补磁力")
        self.assertEqual(link_issue["repair_progress"]["reason_action"], {
            "label": "打开待补磁力候选",
            "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1",
        })

    def test_missing_download_link_issue_links_latest_magnet_failures(self):
        from database import add_download_candidate_event, get_db
        from services.data_quality import build_data_quality_overview

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                ("MIDE-782", "MIDE-782", "补磁力失败", 901, "Actor", "https://example.com/failed.jpg", "supplement", "test", "candidate", ""),
            )
            failed_id = int(cursor.fetchone()["id"])
            cursor.execute(
                """
                INSERT INTO download_candidates
                    (content_id, dvd_id, title, actress_id, actress_name, jacket_thumb_url, source, reason, status, magnet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("MIDE-783", "MIDE-783", "普通待补磁力", 901, "Actor", "https://example.com/pending.jpg", "supplement", "test", "candidate", ""),
            )
        add_download_candidate_event(failed_id, "magnet_enrich_failed", "no magnet found", "manual")

        with patch("services.data_quality.config", Mock(automation_download_policy="manual")):
            result = build_data_quality_overview(limit=20)
        link_issue = next(issue for issue in result["issues"] if issue["type"] == "missing_download_link")

        self.assertEqual(link_issue["repair_progress"]["failed_magnet_enrich"], 1)
        self.assertIn(
            {
                "label": "查看补磁力失败",
                "route": "/downloads?tab=candidates&status=candidate&needs_magnet=1&latest_event_action=magnet_enrich_failed",
            },
            link_issue["repair_progress"]["reason_actions"],
        )

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
        self.assertEqual(cover_issue["repair_progress"]["provider_label"], "来源 avbase 5 · fanza 5 · fc2 5 · jav321 5 · 另 1 个入口")
        self.assertEqual(cover_issue["repair_progress"]["provider_actions"][0]["label"], "查看含 avbase 的失败")
        self.assertEqual(
            cover_issue["repair_progress"]["provider_actions"][0]["route"],
            "/supplement?tab=jobs&status=failed&source=all&error_provider=avbase",
        )

    def test_low_quality_cover_provider_label_marks_folded_route_entries(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-005", "emby-miaa-5", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 12,
                    "provider_failures": [
                        {"provider": "avbase", "count": 5, "route_source": "all"},
                        {"provider": "avbase", "count": 4, "route_source": "avbase"},
                        {"provider": "fanza", "count": 3, "route_source": "all"},
                        {"provider": "fc2", "count": 2, "route_source": "all"},
                        {"provider": "javbus", "count": 1, "route_source": "all"},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["repair_progress"]["provider_label"], "来源 avbase 5 · avbase 4 · fanza 3 · fc2 2 · 另 1 个入口")

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

    def test_low_quality_cover_operational_failures_have_reason_action(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-004", "emby-miaa-4", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 76,
                    "failed_reasons": [
                        {"label": "并发限制", "count": 76},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["repair_progress"]["reason_label"], "失败原因 并发限制 76")
        self.assertEqual(cover_issue["repair_progress"]["reason_action"], {
            "label": "查看失败补全任务",
            "route": "/supplement?tab=jobs&status=failed&error_reason=concurrency_limit",
        })

    def test_low_quality_cover_exposes_secondary_failure_reason_actions(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-005", "emby-miaa-5", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 355,
                    "failed_reasons": [
                        {"label": "来源暂不可用", "count": 256},
                        {"label": "并发限制", "count": 76},
                        {"label": "来源数据结构异常", "count": 8},
                        {"label": "低置信匹配", "count": 8},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(cover_issue["repair_progress"]["reason_action"], {
            "label": "检查补全来源",
            "route": "/supplement?tab=sources",
        })
        self.assertEqual(cover_issue["repair_progress"]["reason_actions"], [
            {
                "label": "查看并发限制失败",
                "route": "/supplement?tab=jobs&status=failed&error_reason=concurrency_limit",
            },
            {
                "label": "查看来源数据结构异常失败",
                "route": "/supplement?tab=jobs&status=failed&error_reason=source_schema",
            },
            {
                "label": "查看低置信匹配失败",
                "route": "/supplement?tab=jobs&status=failed&error_reason=low_confidence",
            },
        ])

    def test_low_quality_cover_reason_label_marks_folded_failures(self):
        from database import upsert_inventory_video
        from services.data_quality import build_data_quality_overview

        upsert_inventory_video("MIAA-006", "emby-miaa-6", 901, "库存标题", "2024-01-01", "")

        result = build_data_quality_overview(
            limit=20,
            repair_progress={
                "low_quality_cover": {
                    "failed": 25,
                    "failed_reasons": [
                        {"label": "来源暂不可用", "count": 9},
                        {"label": "并发限制", "count": 6},
                        {"label": "来源数据结构异常", "count": 4},
                        {"label": "低置信匹配", "count": 3},
                        {"label": "请求失败", "count": 2},
                        {"label": "其他失败", "count": 1},
                    ],
                },
            },
        )

        cover_issue = next(issue for issue in result["issues"] if issue["type"] == "low_quality_cover")
        self.assertEqual(
            cover_issue["repair_progress"]["reason_label"],
            "失败原因 来源暂不可用 9 · 并发限制 6 · 来源数据结构异常 4 · 低置信匹配 3 · 另 3 个原因",
        )

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
