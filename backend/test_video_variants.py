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

    def test_garbled_code_orphan_merges_into_canonical_group_by_title_and_runtime(self):
        # JUMS-154 family — the digital padded id (jums00154) had its dvd_id mis-extracted
        # upstream as "3-5" (probably from the title "35人..." / "460分"). Without a
        # title+runtime salvage pass, it stays an orphan card on the actress page.
        title = "35人の人妻が過去最大級にイキ狂う 膣奥にぶっ刺さるデカチン大絶頂SEX 460分"
        rows = [
            item(content_id="jums154", dvd_id="JUMS-154", title_ja=title, service_code="mono", runtime_mins=460),
            item(content_id="supp547", dvd_id="JUMS-154", title_ja=title, service_code="supplement", runtime_mins=None),
            item(content_id="jums00154", dvd_id="3-5", title_ja=title, service_code="digital", runtime_mins=468),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1, "orphan with garbled dvd_id should fold into the canon group")
        self.assertEqual(grouped[0]["canonical_code"], "JUMS-154")
        self.assertEqual(grouped[0]["variant_group_count"], 3)
        codes = sorted(it.get("dvd_id") or it.get("content_id") for it in grouped[0]["variant_group_items"])
        self.assertIn("3-5", codes)

    def test_garbled_code_orphan_with_mismatched_runtime_is_not_merged(self):
        # Same title, but the orphan's runtime is way off (108 vs 460) → keep separate.
        title = "35人の人妻が過去最大級にイキ狂う 膣奥にぶっ刺さるデカチン大絶頂SEX 460分"
        rows = [
            item(content_id="jums154", dvd_id="JUMS-154", title_ja=title, service_code="mono", runtime_mins=460),
            item(content_id="trailer1", dvd_id="3-5", title_ja=title, service_code="digital", runtime_mins=108),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_garbled_code_orphan_with_short_title_is_not_merged(self):
        # Too-short title can collide across unrelated content — fallback merge must refuse.
        rows = [
            item(content_id="abc123", dvd_id="ABC-123", title_ja="短い", service_code="mono", runtime_mins=120),
            item(content_id="xyz", dvd_id="3-5", title_ja="短い", service_code="digital", runtime_mins=120),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_padded_digit_variants_merge_when_supplement_runtime_is_bogus(self):
        # JUMS-095 / JUMS-95 family — both canonicalise to "JUMS-95" via _trim_digits.
        # The supplement record carried a bogus runtime (255 vs the real ~480) which
        # was vetoing the merge despite identical titles + identical canonical_code.
        title = "美熟女の超S級デカ尻が乱高下するマラ食い騎乗位BEST 102本番8時間"
        rows = [
            item(content_id="jums095", dvd_id="JUMS-095", title_ja=title, service_code="mono", runtime_mins=480),
            item(content_id="jums00095", dvd_id=None, title_ja=title, service_code="digital", runtime_mins=481),
            item(content_id="supp586", dvd_id="JUMS-95", title_ja=title, service_code="supplement", runtime_mins=255),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1, "near-identical titles + same canonical should beat a bogus supplement runtime")
        self.assertEqual(grouped[0]["canonical_code"], "JUMS-95")
        self.assertEqual(grouped[0]["variant_group_count"], 3)

    def test_runtime_divergence_still_splits_when_titles_only_partially_match(self):
        # Sanity check the advisory-runtime relaxation only kicks in for near-identical
        # titles. If titles only partially overlap (≥0.56 but <0.95) and runtimes diverge
        # by >5%, keep them apart — those are plausibly different movies.
        rows = [
            item(content_id="abc001", dvd_id="ABC-001", title_ja="Title BasePart One Different Suffix Here", runtime_mins=120),
            item(content_id="abc1", dvd_id="ABC-1", title_ja="Title BasePart One Slightly Different Tail End", runtime_mins=240),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_dmm_domestic_h_bucket_prefix_is_stripped_for_grouping(self):
        # h_706naac00047b is DMM's "domestic" content id for what FANZA/r18 lists as NAAC-047B.
        # The leading h_<digits> is a maker-bucket marker, not part of the code itself.
        rows = [
            item(
                content_id="naac047b",
                dvd_id="NAAC-047B",
                title_ja="NAAC-047B Title",
                service_code="mono",
                runtime_mins=120,
            ),
            item(
                content_id="h_706naac00047b",
                dvd_id="h_706naac00047b",
                title_ja="NAAC-047B Title",
                service_code="digital",
                runtime_mins=120,
            ),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "NAAC-47")
        self.assertEqual(grouped[0]["variant_group_count"], 2)

    def test_dmm_domestic_h_bucket_rental_suffix_is_stripped_for_grouping(self):
        rows = [
            item(
                content_id="h_906gaso0013",
                dvd_id="GASO-0013",
                title_ja="白石茉莉奈はオレのカノジョ。",
                service_code="digital",
                runtime_mins=146,
            ),
            item(
                content_id="supp:817",
                dvd_id="H-906GASO0013R",
                title_ja="白石茉莉奈はオレのカノジョ。",
                service_code="supplement",
                runtime_mins=None,
            ),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "GASO-13")
        self.assertEqual(grouped[0]["variant_group_count"], 2)

    def test_rental_leading_r_prefix_merges_with_retail_code(self):
        title = "白石茉莉奈 おっぱい吸いながらバブバブ赤ちゃんプレイでオナニーのお手伝いしてあげる"
        rows = [
            item(content_id="1star993", dvd_id="STAR-993", title_ja=title, service_code="mono", runtime_mins=120),
            item(content_id="1star00993", dvd_id=None, title_ja=title, service_code="digital", runtime_mins=121),
            item(content_id="1rstar993r", dvd_id="RSTAR993", title_ja=title, service_code="rental", runtime_mins=120),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "STAR-993")
        self.assertEqual(grouped[0]["variant_group_count"], 3)

    def test_non_rental_leading_r_prefix_does_not_merge(self):
        rows = [
            item(content_id="abc001", dvd_id="ABC-001", title_ja="Shared Title", service_code="mono", runtime_mins=120),
            item(content_id="rabc001", dvd_id="RABC-001", title_ja="Shared Title", service_code="mono", runtime_mins=120),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_real_r_prefix_rental_codes_are_not_stripped(self):
        rows = [
            item(content_id="h_346rebd298r", dvd_id="REBD298", title_ja="Marina5", service_code="rental", runtime_mins=60),
            item(content_id="h_346rebdb284r", dvd_id="REBDB284", title_ja="Marina5", service_code="rental", runtime_mins=60),
        ]

        enriched = video_variants.enrich_video_variants(rows, variant_mode="flat")

        self.assertEqual(enriched[0]["canonical_code"], "REBD-298")
        self.assertEqual(enriched[1]["canonical_code"], "REBDB-284")

    def test_rental_numeric_service_prefix_merges_with_retail_code(self):
        title = "AVファンを熱狂させた伝説企画を、豪華S級女優競演で全編完全撮りおろし！"
        rows = [
            item(content_id="1avop003", dvd_id="AVOP-003", title_ja=title, service_code="mono", runtime_mins=225),
            item(content_id="2avop003", dvd_id="2AVOP003", title_ja=title, service_code="rental", runtime_mins=225),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "AVOP-3")

    def test_digital_padded_content_id_wins_over_misparsed_dvd_id(self):
        title = "悩めるバキバキ童貞にオトナの美女が与える人生最高の射精体験 筆おろしBEST35人 8時間"
        rows = [
            item(content_id="jums131", dvd_id="JUMS-131", title_ja=title, service_code="mono", runtime_mins=480),
            item(content_id="jums00131", dvd_id="BEST-35", title_ja=title, service_code="digital", runtime_mins=481),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "JUMS-131")
        self.assertEqual(grouped[0]["variant_group_count"], 2)

    def test_bluray_code_markers_merge_as_format_variants(self):
        rows = [
            item(content_id="1star444re", dvd_id="STAR-444", title_ja="芸能人 白石茉莉奈 AV Debut", service_code="mono", runtime_mins=200),
            item(content_id="1starbd444re", dvd_id="STARBD-444", title_ja="芸能人 白石茉莉奈 AV Debut", service_code="mono", runtime_mins=200),
            item(content_id="n_1541naac047", dvd_id="NAAC-047", title_ja="Best naked 04/白石茉莉奈", service_code="mono", runtime_mins=111),
            item(content_id="n_1541naac047b", dvd_id="NAAC-047B", title_ja="Best naked 04/白石茉莉奈", service_code="mono", runtime_mins=124),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped", include_explanations=True)
        by_code = {row["canonical_code"]: row for row in grouped}

        self.assertEqual(len(grouped), 2)
        self.assertEqual(by_code["STAR-444"]["variant_group_count"], 2)
        self.assertEqual(by_code["NAAC-47"]["variant_group_count"], 2)
        self.assertIn(
            "蓝光版",
            [label["label"] for item in by_code["STAR-444"]["variant_group_items"] for label in item["variant_labels"]],
        )

    def test_leading_9_bluray_prefix_merges_with_base_code(self):
        title = "世界一豪華な記念作！！ マドンナ20周年記念 湯煙舞う中出し無制限史上初ALL専属バスツアー！！前編"
        rows = [
            item(content_id="juq510", dvd_id="JUQ-510", title_ja=title, service_code="mono", runtime_mins=290),
            item(content_id="9juq510", dvd_id="9JUQ-510", title_ja=title, service_code="mono", runtime_mins=290),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "JUQ-510")

    def test_digit_prefixed_code_family_is_parsed_without_stripping_real_prefix(self):
        title = "【VR】【初VR】リアル結婚生活"
        rows = [
            item(content_id="13dsvr00609", dvd_id="3DSVR-0609", title_ja=title, service_code="digital", runtime_mins=106),
            item(content_id="supp:735", dvd_id="3DSVR609", title_ja=title, service_code="supplement", runtime_mins=106),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "3DSVR-609")

    def test_rental_disc_count_title_marker_merges_with_retail_code(self):
        title = "膣奥の最深を貫く！！デカチンの虜になった人妻30人 8時間"
        rows = [
            item(content_id="4jums039", dvd_id="4JUMS039", title_ja=title + "（2枚組）", service_code="rental", runtime_mins=480, release_date="2024-04-24"),
            item(content_id="jums039", dvd_id="JUMS-039", title_ja=title, service_code="mono", runtime_mins=480, release_date="2023-10-10"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "JUMS-39")

    def test_same_dvd_id_and_release_date_merge_despite_runtime_gap(self):
        rows = [
            item(content_id="n_650ecr0091", dvd_id="ecr-0091", title_ja="エロキュート/白石茉莉奈", service_code="mono", runtime_mins=60, release_date="2016-05-28"),
            item(content_id="h_295ecr00091", dvd_id="ECR-0091", title_ja="エロキュート 白石茉莉奈", service_code="digital", runtime_mins=89, release_date="2016-05-28"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_same_dvd_id_different_release_date_and_title_stays_split(self):
        rows = [
            item(content_id="a1", dvd_id="ABC-12", title_ja="全く別の作品タイトルです", service_code="mono", runtime_mins=120, release_date="2020-01-01"),
            item(content_id="b2", dvd_id="ABC-12", title_ja="こちらは違う内容の映画", service_code="digital", runtime_mins=90, release_date="2021-05-05"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_trailing_bd_token_with_bluray_marker_merges_despite_runtime_gap(self):
        rows = [
            item(content_id="n_1473gtrp004", dvd_id="GTRP-004", title_ja="Marilyn Holiday 〜ある夜の出来事〜/白石茉莉奈", service_code="mono", runtime_mins=70, release_date="2019-12-28"),
            item(content_id="h_706gtrp00004b", dvd_id="GTRP-004B", title_ja="Marilyn Holiday ～ある夜の出来事～/白石茉莉奈 BD", service_code="digital", runtime_mins=95, release_date="2019-12-28"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "GTRP-4")

    def test_search_codes_prefer_padded_display_form(self):
        codes = video_variants.search_codes_for_item(
            {"content_id": "4jums039", "dvd_id": "4JUMS039", "service_code": "rental", "title_ja": "x"}
        )
        self.assertEqual(codes[0], "JUMS-039")
        self.assertIn("JUMS-39", codes)
        self.assertIn("4JUMS039", codes)

    def test_search_codes_for_h_bucket_content_id(self):
        codes = video_variants.search_codes_for_item(
            {"content_id": "h_706gtrp00004b", "dvd_id": "GTRP-004B", "service_code": "digital", "title_ja": "x BD"}
        )
        # The Blu-ray edition marker is stripped for the primary search form
        # (releases are named after the base code); the raw dvd_id stays as a
        # fallback alias.
        self.assertEqual(codes[0], "GTRP-004")
        self.assertIn("GTRP-004B", codes)

    def test_search_codes_fc2(self):
        codes = video_variants.search_codes_for_item(
            {"content_id": "", "dvd_id": "FC2-PPV-1234567", "service_code": "supplement", "title_ja": "x"}
        )
        self.assertEqual(codes[0], "FC2-PPV-1234567")
        self.assertIn("FC2-1234567", codes)

    def test_filter_movie_items_drops_ebooks(self):
        rows = [
            item(content_id="k568agotp00164", dvd_id="2-020", service_code="ebook"),
            item(content_id="jums039", dvd_id="JUMS-039", service_code="mono"),
        ]
        kept = video_variants.filter_movie_items(rows)
        self.assertEqual([row["content_id"] for row in kept], ["jums039"])


if __name__ == "__main__":
    unittest.main()
