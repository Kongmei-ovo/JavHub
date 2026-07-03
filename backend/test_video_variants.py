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

    def test_grouped_primary_borrows_digital_sibling_cover(self):
        rows = [
            item(
                content_id="jur740",
                dvd_id="JUR-740",
                service_code="mono",
                jacket_thumb_url="https://awsimgsrc.dmm.com/dig/mono/movie/jur740/jur740ps.jpg",
            ),
            item(
                content_id="jur00740",
                dvd_id=None,
                service_code="digital",
                jacket_thumb_url="https://awsimgsrc.dmm.com/dig/digital/video/jur00740/jur00740ps.jpg",
                jacket_full_url="digital/video/jur00740/jur00740pl",
            ),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        primary = grouped[0]
        # Identity stays the DVD code, but the merged card borrows the digital cover.
        self.assertEqual(primary["display_code"], "JUR-740")
        self.assertIn("/digital/video/", primary["jacket_thumb_url"])
        self.assertEqual(primary["jacket_full_url"], "digital/video/jur00740/jur00740pl")
        # The per-variant breakdown still keeps each variant's own cover.
        covers = {e["content_id"]: e.get("jacket_thumb_url") for e in primary["variant_group_items"]}
        self.assertIn("/mono/movie/", covers["jur740"])
        self.assertIn("/digital/video/", covers["jur00740"])

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

    def test_storefront_runtime_discrepancy_merges_within_week(self):
        # mono vs digital list the same product number with diverging runtimes
        # and a few days' gap (DMDG-060: 130 vs 118 mins, 3 days apart).
        rows = [
            item(content_id="dmdg060", dvd_id="DMDG-060", title_ja="マゾ乳中出し Iカップ 田中ねね", service_code="mono", runtime_mins=130, release_date="2025-04-15"),
            item(content_id="dmdg00060", dvd_id="", title_ja="マゾ乳中出し Iカップ 田中ねね", service_code="digital", runtime_mins=118, release_date="2025-04-12"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_same_storefront_runtime_divergence_still_splits(self):
        # Same storefront (mono+mono), same title, big runtime gap → keep the
        # strict runtime veto (DOD re-pressings, multi-part discs).
        rows = [
            item(content_id="miaa00784", dvd_id="MIAA-784", title_ja="Same Title", service_code="mono", runtime_mins=170, release_date="2023-02-21"),
            item(content_id="miaa00784dod", dvd_id="MIAA-784DOD", title_ja="Same Title （DOD）", service_code="mono", runtime_mins=220, release_date="2023-02-21"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_identical_date_cross_storefront_relaxes_low_number_threshold(self):
        # GRACE-023: mono "/女優名" vs digital " 女優名" drops similarity below
        # the strict low-number bar, but same-day cross-storefront is decisive.
        rows = [
            item(content_id="n_1535grace023", dvd_id="GRACE-023", title_ja="爆乳プリンセス/田中ねね", service_code="mono", runtime_mins=128, release_date="2025-04-30"),
            item(content_id="h_1714grace00023", dvd_id="", title_ja="爆乳プリンセス 田中ねね", service_code="digital", runtime_mins=129, release_date="2025-04-30"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_bonus_tail_with_donor_name_is_stripped(self):
        # 【FANZA限定】 + "吉根ゆりあさんのパンティと生写真付き" tail must key
        # identically to the base title (USBA-071 vs TKUSBA-071).
        rows = [
            item(content_id="usba071", dvd_id="USBA-071", title_ja="露出マゾ 爆乳豊満W肉便器野外調教", service_code="mono", runtime_mins=108, release_date="2023-12-26"),
            item(content_id="tkusba071", dvd_id="TKUSBA-071", title_ja="【FANZA限定】露出マゾ 爆乳豊満W肉便器野外調教 吉根ゆりあさんのパンティと生写真付き", service_code="mono", runtime_mins=108, release_date="2023-12-27"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "USBA-71")

    def test_title_level_bluray_evidence_bypasses_runtime_veto(self):
        # 数量限定 Blu-ray チェキ edition keeps the base code; Blu-ray evidence
        # only exists in the title (SS-127BTK, 94 vs 84 mins).
        rows = [
            item(content_id="n_1428ss127", dvd_id="SS-127", title_ja="Curvaceous/田中ねね", service_code="mono", runtime_mins=84, release_date="2025-02-01"),
            item(content_id="n_1428ss127btk", dvd_id="SS-127BTK", title_ja="【数量限定】Curvaceous/田中ねね （ブルーレイディスク） チェキ付き", service_code="mono", runtime_mins=94, release_date="2025-02-01"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_junk_dvd_id_falls_back_to_content_id(self):
        # Compilation rows carry garbage dvd_ids like "2-023" while the
        # content_id parses cleanly (7xvsr701 → XVSR-701).
        rows = [
            item(content_id="7xvsr701", dvd_id="2-023", title_ja="【ベストヒッツ】MGC ACT.2", service_code="mono", runtime_mins=280, release_date="2026-04-20"),
        ]

        flat = video_variants.enrich_video_variants(rows, variant_mode="flat")

        self.assertEqual(flat[0]["canonical_code"], "XVSR-701")

    def test_two_year_rerelease_merges_across_storefronts(self):
        # Identical title, same code, storefront listings two years apart
        # (GHOV-51): a re-listed product is still the same work — the date
        # window was dropped deliberately (round 3, 篠田ゆう audit).
        rows = [
            item(content_id="h_173ghov00051", dvd_id="", title_ja="女幹部ガーベラ ヒーロー逆NTR", service_code="digital", runtime_mins=131, release_date="2024-08-01"),
            item(content_id="h_173ghov51", dvd_id="", title_ja="女幹部ガーベラ ヒーロー逆NTR", service_code="mono", runtime_mins=120, release_date="2022-07-22"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_rental_cut_with_shorter_runtime_merges(self):
        # Rental discs are trimmed cuts of the retail product (JUC-602: 90 vs
        # 120 mins, identical title).
        title = "若妻羞恥バス痴● 篠田ゆう〜工場に勤める若妻の通勤凌●〜"
        rows = [
            item(content_id="5juc602", dvd_id="5JUC602", title_ja=title, service_code="rental", runtime_mins=90, release_date="2012-02-24"),
            item(content_id="juc602", dvd_id="JUC-602", title_ja=title, service_code="mono", runtime_mins=120, release_date="2011-08-07"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_rental_subtitle_swap_merges_with_loose_gate(self):
        # SCF-008: the rental listing swaps the subtitle for "4時間"; rental ↔
        # retail with the same code is the same product, so the loose 0.5 gate
        # applies.
        rows = [
            item(content_id="832scf008", dvd_id="2SCF008", title_ja="対面オナニー＆相互愛撫 4時間", service_code="rental", runtime_mins=240, release_date="2013-05-24"),
            item(content_id="83scf008", dvd_id="SCF-008", title_ja="対面オナニー＆相互愛撫 厳選淫乱女優24名！！", service_code="mono", runtime_mins=240, release_date="2013-01-13"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_rental_pair_with_unrelated_title_stays_split(self):
        rows = [
            item(content_id="r1", dvd_id="ABC-12", title_ja="全く別の作品タイトルです", service_code="rental", runtime_mins=120, release_date="2010-01-01"),
            item(content_id="r2", dvd_id="ABC-12", title_ja="こちらは違う内容の映画", service_code="mono", runtime_mins=90, release_date="2013-05-05"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_reedited_digital_with_embedded_code_paren_merges(self):
        # NACX-066: the 2024 digital re-edit embeds its own code in the title
        # （NACX-066SA1jo01） and drops one performer (14人→13人).
        rows = [
            item(content_id="h_237nacx00066sa1jo1", dvd_id="NACX-066", title_ja="くねらす絶品ボディ中出し13人VOL.02（NACX-066SA1jo01）", service_code="digital", runtime_mins=226, release_date="2024-01-23"),
            item(content_id="h_237nacx066", dvd_id="NACX-066", title_ja="くねらす絶品ボディ中出し14人VOL.02", service_code="mono", runtime_mins=243, release_date="2020-11-01"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_outlet_reissue_with_truncated_title_merges(self):
        # GVG-299: アウトレット re-release truncates the title; runtime equal.
        rows = [
            item(content_id="7gvg299", dvd_id="5GVG-299", title_ja="【アウトレット】母子姦 篠田あゆみ", service_code="mono", runtime_mins=120, release_date="2018-09-20"),
            item(content_id="13gvg299", dvd_id="GVG-299", title_ja="母子姦 息子の巨根に欲情した巨乳母 篠田あゆみ", service_code="mono", runtime_mins=120, release_date="2016-05-05"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_cross_language_titles_fall_back_to_code_and_runtime(self):
        # BUG-020: digital row only has title_en, mono only title_ja — a JA/EN
        # similarity comparison is meaningless and must not veto the merge.
        rows = [
            item(content_id="h_918bug00020", dvd_id="BUG-020", title_ja=None, title_en="Gold Dust S***e Soapland Ayumi Shinoda", service_code="digital", runtime_mins=137, release_date="2016-05-31"),
            item(content_id="h_918bug020", dvd_id="BUG-020", title_ja="金粉奴●ソープ 篠田あゆみ", service_code="mono", runtime_mins=136, release_date="2015-11-20"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_parseable_junk_dvd_id_yields_to_content_id_identity(self):
        # r18 dump rows where dvd_id is title-derived garbage ("BEST-480" from
        # 神乳BEST480分) while the content_id is the real code (bf767/bf00767).
        rows = [
            item(content_id="bf767", dvd_id="BEST-480", title_ja="神乳BEST480分", service_code="mono", runtime_mins=480, release_date="2026-07-07"),
            item(content_id="bf00767", dvd_id="BEST-480", title_ja="神乳BEST480分", service_code="digital", runtime_mins=480, release_date="2026-07-03"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "BF-767")
        self.assertEqual(video_variants.search_codes_for_item(rows[0])[0], "BF-767")

    def test_content_id_identity_override_guards_hold(self):
        # Bonus TK prefix, n_/h_ bucket cids and rental digit prefixes must NOT
        # trigger the override — their dvd_id is authoritative.
        keep_dvd = [
            ({"content_id": "tkusba071", "dvd_id": "TKUSBA-071", "service_code": "mono", "title_ja": "【FANZA限定】露出マゾ パンティと生写真付き"}, "USBA-71"),
            ({"content_id": "n_1428ss127btk", "dvd_id": "SS-127BTK", "service_code": "mono", "title_ja": "【数量限定】Curvaceous （ブルーレイディスク） チェキ付き"}, "SS-127"),
            ({"content_id": "1rsshn002r", "dvd_id": "RSSHN002", "service_code": "rental", "title_ja": "x（2枚組）"}, "SSHN-2"),
        ]
        for row, want in keep_dvd:
            flat = video_variants.enrich_video_variants([item(**row)], variant_mode="flat")
            self.assertEqual(flat[0]["canonical_code"], want, row["content_id"])

    def test_store_digit_prefixed_group_folds_into_base_group(self):
        # Store-digit reissue rows keep the digit in BOTH dvd_id and content_id
        # (7usba071 / 7USBA-071), so only group-level adoption can fold them
        # into the base USBA-071 group.
        title = "露出マゾ 爆乳豊満W肉便器野外調教"
        rows = [
            item(content_id="usba071", dvd_id="USBA-071", title_ja=title, service_code="mono", runtime_mins=108, release_date="2023-12-26"),
            item(content_id="7usba071", dvd_id="7USBA-071", title_ja=title, service_code="mono", runtime_mins=108, release_date="2023-12-26"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "USBA-71")
        self.assertEqual(grouped[0]["variant_group_count"], 2)

    def test_digit_prefixed_group_with_different_title_stays_split(self):
        rows = [
            item(content_id="umso533", dvd_id="UMSO-533", title_ja="完全に別の作品タイトルA", service_code="mono", runtime_mins=120, release_date="2024-01-01"),
            item(content_id="7umso533", dvd_id="7UMSO-533", title_ja="別内容の格安版コンピレーション", service_code="mono", runtime_mins=240, release_date="2020-05-05"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 2)

    def test_rental_with_retitled_listing_merges(self):
        # FCDC-090: the rental listing prepends extra copy and the mono row
        # appends performer names; rental ↔ retail same code = same product.
        rows = [
            item(content_id="h_114fcdc090r", dvd_id="FCDC090", title_ja="社内の営業部はパツパツマイクロミニスカートで社員を挑発するヤリマンドスケベ巨乳OL", service_code="rental", runtime_mins=110, release_date="2017-12-21"),
            item(content_id="fcdc090", dvd_id="FCDC-090", title_ja="マイクロミニスカートで社員を挑発するヤリマンドスケベ巨乳OL 羽生ありさ 西村ニーナ", service_code="mono", runtime_mins=110, release_date="2017-10-25"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_bromide_bonus_edition_merges(self):
        # AEGE-012TK: 数量限定 + ブロマイド3種付き store bonus.
        rows = [
            item(content_id="1aege012", dvd_id="AEGE-012", title_ja="黒人覚醒 巨乳VSデカチン 吉根ゆりあ", service_code="mono", runtime_mins=125, release_date="2023-08-24"),
            item(content_id="1aege012tk", dvd_id="AEGE-012TK", title_ja="【数量限定】黒人覚醒 巨乳VSデカチン 吉根ゆりあ ブロマイド3種付き", service_code="mono", runtime_mins=125, release_date="2023-08-24"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["canonical_code"], "AEGE-12")

    def test_short_title_with_name_suffix_merges_same_day_cross_storefront(self):
        # GRACE-008: "Mの世界/吉根ゆりあ" vs "Mの世界 吉根ゆりあ" — prefix
        # containment on the same day across storefronts.
        rows = [
            item(content_id="n_1535grace008", dvd_id="GRACE-008", title_ja="Mの世界/吉根ゆりあ", service_code="mono", runtime_mins=90, release_date="2023-04-21"),
            item(content_id="h_1714grace00008", dvd_id="", title_ja="Mの世界 吉根ゆりあ", service_code="digital", runtime_mins=91, release_date="2023-04-21"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_rental_truncated_title_prefix_merges(self):
        # SET-020: the rental listing truncates the long mono title; prefix
        # containment counts for rental↔retail pairs.
        long_title = "kira★kira STREET GAL＆おやじっち 中年の俺が家事代行サービスを頼んだら、とびきり可愛いギャル2人がやってきた。家事は完璧にこなしエロサービスは満点で…"
        rows = [
            item(content_id="4set020", dvd_id="4SET020", title_ja=long_title[:58], service_code="rental", runtime_mins=150, release_date="2015-02-24"),
            item(content_id="set020", dvd_id="SET-020", title_ja=long_title, service_code="mono", runtime_mins=150, release_date="2014-11-19"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_prefix_containment_within_week_cross_storefront_merges(self):
        # ACHJ-084: digital appends the performer name, releases 4 days apart.
        rows = [
            item(content_id="achj084", dvd_id="", title_ja="人権無視の見下し淫語×張りパイ暴力でM男を徹底的に躾けるブラック保育園", service_code="mono", runtime_mins=170, release_date="2026-05-12"),
            item(content_id="achj00084", dvd_id="", title_ja="人権無視の見下し淫語×張りパイ暴力でM男を徹底的に躾けるブラック保育園 風間ゆみ", service_code="digital", runtime_mins=175, release_date="2026-05-08"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_own_code_embedded_in_title_is_stripped_symmetrically(self):
        # TSX-19: the mono title starts with its own product code.
        rows = [
            item(content_id="h_1311tsx19", dvd_id="TSX-19", title_ja="TSX-19 美尻痴女 Fetishist19 蓮実クレア", service_code="mono", runtime_mins=150, release_date="2018-06-04"),
            item(content_id="h_1072tsx00019", dvd_id="TSX-19", title_ja="美尻痴女 Fetishist19 蓮実クレア", service_code="digital", runtime_mins=154, release_date="2018-05-28"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)

    def test_reissue_paren_and_hivision_edition_markers_are_stripped(self):
        # AVOP-372 （2017AVOPEN参加作品再販） and MXBD-005 Hi-Vision特別編.
        avop = video_variants.enrich_video_variants([
            item(content_id="2avop372ta", dvd_id="AVOP-372", title_ja="熟シャッ！！ W SEXとスペレズと美熟女 （2017AVOPEN参加作品再販）", service_code="mono", runtime_mins=180, release_date="2018-05-04"),
            item(content_id="2avop00372", dvd_id="AVOP-372", title_ja="熟シャッ！！ W SEXとスペレズと美熟女", service_code="digital", runtime_mins=184, release_date="2017-09-01"),
        ], variant_mode="grouped")
        self.assertEqual(len(avop), 1)

        mxbd = video_variants.enrich_video_variants([
            item(content_id="h_068mxbd00005", dvd_id="MXBD-005", title_ja="美熟女 Venus Port 翔田千里＆風間ゆみ", service_code="digital", runtime_mins=119, release_date="2009-10-03"),
            item(content_id="h_068mxbd005", dvd_id="MXBD-005", title_ja="美熟女 Venus Port 翔田千里＆風間ゆみ Hi-Vision特別編（ブルーレイディスク）", service_code="mono", runtime_mins=120, release_date="2008-04-25"),
        ], variant_mode="grouped")
        self.assertEqual(len(mxbd), 1)

    def test_prefix_containment_runtime_bypass_same_day(self):
        # SAN-342: same-day mono/digital, 120 vs 129 mins, name-suffix title.
        rows = [
            item(content_id="h_796san342", dvd_id="SAN-342", title_ja="義理の息子の若チンを味わったら止まらなくなった義母 / 翔田千里", service_code="mono", runtime_mins=120, release_date="2025-04-29"),
            item(content_id="h_796san00342", dvd_id="", title_ja="義理の息子の若チンを味わったら止まらなくなった義母 翔田千里", service_code="digital", runtime_mins=129, release_date="2025-04-29"),
        ]

        grouped = video_variants.enrich_video_variants(rows, variant_mode="grouped")

        self.assertEqual(len(grouped), 1)


if __name__ == "__main__":
    unittest.main()
