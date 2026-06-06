from __future__ import annotations

import unittest

from services import video_variants


def item(**overrides):
    data = {
        "content_id": "miaa00784",
        "dvd_id": "MIAA-784",
        "title_ja": "M男クン家にデカ尻ギャルGOGOデリバリー！ 乙アリス 弥生みづき",
        "service_code": "mono",
        "release_date": "2023-02-21",
        "runtime_mins": 170,
        "actresses": [{"id": 1, "name_kanji": "乙アリス"}, {"id": 2, "name_kanji": "弥生みづき"}],
    }
    data.update(overrides)
    return data


class VideoVariantAnalysisTest(unittest.TestCase):
    def test_labels_standard_digital_rental_and_on_demand_variants(self):
        rows = [
            item(content_id="miaa00784", dvd_id="MIAA-784", service_code="mono"),
            item(content_id="miaa00784", dvd_id=None, service_code="digital"),
            item(content_id="4miaa784", dvd_id="4MIAA784", service_code="rental"),
            item(content_id="miaa00784bod", dvd_id="MIAA-784BOD", service_code="mono"),
            item(content_id="miaa00784dod", dvd_id="MIAA-784DOD", service_code="mono"),
            item(content_id="miaa00784rdod", dvd_id="MIAA-784RDOD", service_code="mono"),
        ]

        enriched = video_variants.enrich_video_variants(rows, variant_mode="flat", include_explanations=True)
        by_code = {row["dvd_id"] or row["content_id"]: row for row in enriched}

        self.assertEqual(by_code["MIAA-784"]["canonical_code"], "MIAA-784")
        self.assertEqual(by_code["miaa00784"]["display_code"], "MIAA-784")
        self.assertIn("数字版", [label["label"] for label in by_code["miaa00784"]["variant_labels"]])
        self.assertIn("租赁版", [label["label"] for label in by_code["4MIAA784"]["variant_labels"]])
        self.assertIn("BOD 蓝光按需", [label["label"] for label in by_code["MIAA-784BOD"]["variant_labels"]])
        self.assertIn("DOD 按需DVD", [label["label"] for label in by_code["MIAA-784DOD"]["variant_labels"]])
        self.assertIn("DOD 按需DVD", [label["label"] for label in by_code["MIAA-784RDOD"]["variant_labels"]])
        self.assertEqual(by_code["MIAA-784BOD"]["variant_explanations"][0]["source"], "official")

    def test_tk_prefix_is_limited_bonus_only_with_title_evidence(self):
        limited = item(
            content_id="tkmiaa00784",
            dvd_id="TKMIAA-784",
            title_ja="【FANZA限定】M男クン家にデカ尻ギャルGOGOデリバリー！ 生写真3枚付き",
        )
        real_prefix = item(
            content_id="tkyd00003",
            dvd_id="TKYD-03",
            title_ja="通常作品タイトル",
        )

        enriched = video_variants.enrich_video_variants([limited, real_prefix], variant_mode="flat", include_explanations=True)
        limited_labels = [label["label"] for label in enriched[0]["variant_labels"]]
        real_labels = [label["label"] for label in enriched[1]["variant_labels"]]

        self.assertEqual(enriched[0]["canonical_code"], "MIAA-784")
        self.assertIn("FANZA限定特典", limited_labels)
        self.assertEqual(enriched[1]["canonical_code"], "TKYD-3")
        self.assertNotIn("FANZA限定特典", real_labels)

    def test_grouping_collapses_safe_variants_and_keeps_group_items(self):
        rows = [
            item(content_id="miaa00784", dvd_id="MIAA-784", service_code="mono"),
            item(content_id="tkmiaa00784", dvd_id="TKMIAA-784", title_ja="【FANZA限定】M男クン家にデカ尻ギャルGOGOデリバリー！ 生写真3枚付き"),
            item(content_id="miaa00784bod", dvd_id="MIAA-784BOD", title_ja="M男クン家にデカ尻ギャルGOGOデリバリー！ （BOD）"),
            item(content_id="miaa00784", dvd_id=None, service_code="digital"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped", include_explanations=True)

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["display_code"], "MIAA-784")
        self.assertEqual(grouped[0]["variant_group_count"], 4)
        self.assertEqual([entry["display_code"] for entry in grouped[0]["variant_group_items"]], ["MIAA-784", "MIAA-784", "MIAA-784BOD", "TKMIAA-784"])
        self.assertEqual(grouped[0]["variant_group_items"][1]["content_id"], "miaa00784")

    def test_grouping_keeps_search_result_order(self):
        rows = [
            item(content_id="zzzz00150", dvd_id="ZZZZ-150", title_ja="Later Title", release_date="2024-01-01"),
            item(content_id="miaa00784bod", dvd_id="MIAA-784BOD", title_ja="Title （BOD）", release_date="2023-02-21"),
            item(content_id="miaa00784", dvd_id="MIAA-784", title_ja="Title", release_date="2023-02-20"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual([row["display_code"] for row in grouped], ["ZZZZ-150", "MIAA-784"])

    def test_grouping_allows_far_release_dates_but_still_requires_runtime_and_actors_when_present(self):
        baseline = item(
            content_id="miaa00784",
            dvd_id="MIAA-784",
            title_ja="Same Title",
            release_date="2023-02-21",
            runtime_mins=170,
            actresses=[{"id": 1, "name_kanji": "乙アリス"}],
        )

        far_date = video_variants.enrich_video_variants(
            [
                baseline,
                item(content_id="miaa00784bod", dvd_id="MIAA-784BOD", title_ja="Same Title （BOD）", release_date="2024-02-21"),
            ],
            variant_mode="grouped",
        )
        far_runtime = video_variants.enrich_video_variants(
            [
                baseline,
                item(content_id="miaa00784dod", dvd_id="MIAA-784DOD", title_ja="Same Title （DOD）", runtime_mins=220),
            ],
            variant_mode="grouped",
        )
        different_actor = video_variants.enrich_video_variants(
            [
                baseline,
                item(
                    content_id="tkmiaa00784",
                    dvd_id="TKMIAA-784",
                    title_ja="【FANZA限定】Same Title 生写真付き",
                    actresses=[{"id": 99, "name_kanji": "別演员"}],
                ),
            ],
            variant_mode="grouped",
        )

        self.assertEqual(len(far_date), 1)
        self.assertEqual(far_date[0]["variant_group_count"], 2)
        self.assertEqual(len(far_runtime), 2)
        self.assertEqual(len(different_actor), 1)

    def test_short_reused_codes_are_grouped_when_title_and_runtime_match(self):
        rows = [
            item(
                content_id="sbb055",
                dvd_id="SBB-055",
                title_ja="Low Number Same Movie",
                release_date="2010-01-01",
                runtime_mins=83,
            ),
            item(
                content_id="sbb00055",
                dvd_id="SBB-00055",
                title_ja="Low Number Same Movie",
                release_date="2019-01-01",
                runtime_mins=83,
            ),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "SBB-55")
        self.assertEqual(grouped[0]["variant_group_count"], 2)

    def test_short_reused_codes_are_not_grouped_when_title_differs(self):
        rows = [
            item(content_id="jkd001", dvd_id="JKD-001", title_ja="Title A", release_date="2010-01-01"),
            item(content_id="jkd01", dvd_id="JKD-01", title_ja="Completely Different Title", release_date="2020-01-01"),
            item(content_id="ss023", dvd_id="SS-023", title_ja="Other A"),
            item(content_id="ss0023", dvd_id="SS-0023", title_ja="Other B"),
            item(content_id="rpd001", dvd_id="RPD-001", title_ja="RPD A"),
            item(content_id="rpd01", dvd_id="RPD-01", title_ja="RPD B"),
            item(content_id="ssd003", dvd_id="SSD-003", title_ja="SSD A"),
            item(content_id="ssd03", dvd_id="SSD-03", title_ja="SSD B"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), len(rows))
        self.assertTrue(all(row["variant_group_count"] == 1 for row in grouped))

    def test_rd_family_cross_year_variants_are_grouped_by_title_and_runtime(self):
        rows = [
            item(content_id="rd153dod", dvd_id="RD-153DOD", title_ja="RD Family Title", service_code="mono", release_date="2019-06-21", runtime_mins=83),
            item(content_id="rd000153", dvd_id="RD-000153", title_ja="RD Family Title", service_code="mono", release_date="2008-01-25", runtime_mins=83),
            item(content_id="rd153", dvd_id="RD-153", title_ja="RD Family Title", service_code="digital", release_date="2008-01-12", runtime_mins=82),
            item(content_id="rd153rental", dvd_id="RD153", title_ja="RD Family Title", service_code="rental", release_date="2006-12-22", runtime_mins=83),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "RD-153")
        self.assertEqual(grouped[0]["variant_group_count"], 4)

    def test_grouping_clusters_within_bucket_so_one_outlier_does_not_block_the_rest(self):
        rows = [
            item(content_id="rd00153", dvd_id="RD-153", title_ja="Shared Movie Title", release_date="2008-01-12", runtime_mins=82),
            item(content_id="rd000153", dvd_id="RD-000153", title_ja="Shared Movie Title", release_date="2008-01-25", runtime_mins=83),
            item(content_id="rd153dod", dvd_id="RD-153DOD", title_ja="Shared Movie Title", release_date="2019-06-21", runtime_mins=83),
            item(content_id="rd153other", dvd_id="RD153", title_ja="Completely Different Movie", release_date="2019-06-21", runtime_mins=83),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)
        grouped_counts = sorted(row["variant_group_count"] for row in grouped)
        self.assertEqual(grouped_counts, [1, 3])


if __name__ == "__main__":
    unittest.main()
