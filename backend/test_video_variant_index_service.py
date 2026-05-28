from __future__ import annotations

import unittest
from unittest.mock import patch

from test_support.postgres import TempPostgresMixin


class VideoVariantIndexServiceTest(TempPostgresMixin, unittest.TestCase):
    def test_build_variant_index_groups_uses_safe_grouping_and_low_number_guard(self):
        from services.video_variant_index import build_variant_index_groups

        rows = [
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono", "release_date": "2023-02-21", "runtime_mins": 170},
            {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital", "release_date": "2023-02-17", "runtime_mins": 171},
            {"content_id": "miaa784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title （BOD）", "service_code": "mono", "release_date": "2023-02-21", "runtime_mins": 170},
            {"content_id": "tkmiaa784", "dvd_id": "TKMIAA-784", "title_ja": "【FANZA限定】Title 生写真付き", "service_code": "mono", "release_date": "2023-02-22", "runtime_mins": 170},
            {"content_id": "jkd001", "dvd_id": "JKD-01", "title_ja": "Low One", "service_code": "mono"},
            {"content_id": "jkd00001", "dvd_id": None, "title_ja": "Different Low", "service_code": "digital"},
        ]

        groups = build_variant_index_groups(rows)

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["canonical_code"], "MIAA-784")
        self.assertEqual(group["group_count"], 4)
        self.assertEqual(group["primary_content_id"], "miaa784")
        labels = [
            label["key"]
            for item in group["items"]
            for label in item.get("variant_labels", [])
        ]
        self.assertIn("digital", labels)
        self.assertIn("bod", labels)
        self.assertIn("fanza_bonus", labels)

    def test_apply_indexed_variant_groups_injects_global_group_and_falls_back_when_empty(self):
        from database.video_variant_index import replace_variant_groups
        from services.video_variant_index import apply_indexed_variant_groups

        replace_variant_groups(
            [
                {
                    "group_id": "vg:miaa784",
                    "canonical_code": "MIAA-784",
                    "primary_content_id": "miaa784",
                    "group_count": 3,
                    "confidence": "high",
                    "items": [
                        {"content_id": "miaa784", "dvd_id": "MIAA-784", "display_code": "MIAA-784", "service_code": "mono", "variant_labels": [], "sort_rank": 0},
                        {"content_id": "miaa00784", "dvd_id": None, "display_code": "MIAA-784", "service_code": "digital", "variant_labels": [{"key": "digital", "label": "数字版", "short_label": "数字"}], "sort_rank": 1},
                        {"content_id": "miaa784bod", "dvd_id": "MIAA-784BOD", "display_code": "MIAA-784BOD", "service_code": "mono", "variant_labels": [{"key": "bod", "label": "BOD 蓝光按需", "short_label": "BOD"}], "sort_rank": 2},
                    ],
                }
            ]
        )

        indexed = apply_indexed_variant_groups(
            [
                {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital"},
                {"content_id": "other", "dvd_id": "ABCD-123", "title_ja": "Other", "service_code": "mono"},
            ],
            include_explanations=False,
        )

        self.assertEqual(len(indexed), 2)
        self.assertTrue(indexed[0]["variant_indexed"])
        self.assertEqual(indexed[0]["variant_group_count"], 3)
        self.assertEqual([item["content_id"] for item in indexed[0]["variant_group_items"]], ["miaa784", "miaa00784", "miaa784bod"])
        self.assertEqual(indexed[1]["variant_group_count"], 1)
        self.assertFalse(indexed[1].get("variant_indexed", False))

    def test_apply_indexed_variant_groups_keeps_every_paged_row_when_group_members_share_page(self):
        from database.video_variant_index import replace_variant_groups
        from services.video_variant_index import apply_indexed_variant_groups

        replace_variant_groups(
            [
                {
                    "group_id": "vg:miaa784",
                    "canonical_code": "MIAA-784",
                    "primary_content_id": "miaa784",
                    "group_count": 3,
                    "confidence": "high",
                    "items": [
                        {"content_id": "miaa784", "dvd_id": "MIAA-784", "display_code": "MIAA-784", "service_code": "mono", "variant_labels": [], "sort_rank": 0},
                        {"content_id": "miaa00784", "dvd_id": None, "display_code": "MIAA-784", "service_code": "digital", "variant_labels": [{"key": "digital", "label": "数字版", "short_label": "数字"}], "sort_rank": 1},
                        {"content_id": "miaa784bod", "dvd_id": "MIAA-784BOD", "display_code": "MIAA-784BOD", "service_code": "mono", "variant_labels": [{"key": "bod", "label": "BOD 蓝光按需", "short_label": "BOD"}], "sort_rank": 2},
                    ],
                }
            ]
        )

        indexed = apply_indexed_variant_groups(
            [
                {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono"},
                {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital"},
                {"content_id": "miaa784bod", "dvd_id": "MIAA-784BOD", "title_ja": "Title BOD", "service_code": "mono"},
            ]
        )

        self.assertEqual([item["content_id"] for item in indexed], ["miaa784", "miaa00784", "miaa784bod"])
        self.assertEqual([item["variant_group_count"] for item in indexed], [3, 3, 3])
        self.assertTrue(all(item["variant_indexed"] for item in indexed))

    def test_run_variant_index_job_keeps_old_index_when_build_fails(self):
        from database.video_variant_index import (
            add_variant_group_job,
            get_variant_group_by_content_ids,
            get_variant_group_job,
            replace_variant_groups,
        )
        from services.video_variant_index import run_variant_index_job

        replace_variant_groups(
            [
                {
                    "group_id": "vg:old",
                    "canonical_code": "OLD-100",
                    "primary_content_id": "old100",
                    "group_count": 2,
                    "confidence": "high",
                    "items": [
                        {"content_id": "old100", "dvd_id": "OLD-100", "display_code": "OLD-100", "service_code": "mono"},
                        {"content_id": "old00100", "display_code": "OLD-100", "service_code": "digital"},
                    ],
                }
            ]
        )
        job_id = add_variant_group_job()

        with patch("services.video_variant_index.scan_derived_video_rows", side_effect=RuntimeError("scan failed")):
            result = run_variant_index_job(job_id)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(get_variant_group_job(job_id)["status"], "failed")
        self.assertEqual(get_variant_group_by_content_ids(["old100"])["old100"]["group_id"], "vg:old")

    def test_run_variant_index_job_purges_response_cache_after_successful_rebuild(self):
        from database.video_variant_index import add_variant_group_job
        from services.video_variant_index import run_variant_index_job

        rows = [
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Title", "service_code": "mono", "release_date": "2023-02-21", "runtime_mins": 170},
            {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Title", "service_code": "digital", "release_date": "2023-02-17", "runtime_mins": 171},
        ]
        job_id = add_variant_group_job()

        with patch("services.video_variant_index.scan_derived_video_rows", return_value=rows), \
             patch("services.video_variant_index.hydrate_rows_with_actresses", side_effect=lambda value: value), \
             patch("services.cache.purge_response_cache", return_value=7) as purge:
            result = run_variant_index_job(job_id)

        self.assertEqual(result["status"], "completed")
        purge.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
