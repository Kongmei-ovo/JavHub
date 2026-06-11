"""Pure grouping tests for the variant index builder (no postgres needed)."""
from __future__ import annotations

import unittest

from services.video_variant_index import _bucket_key, build_variant_index_groups


def row(**overrides):
    data = {
        "content_id": "usba071",
        "dvd_id": "USBA-071",
        "title_ja": "露出マゾ 爆乳豊満W肉便器野外調教",
        "service_code": "mono",
        "release_date": "2023-12-26",
        "runtime_mins": 108,
    }
    data.update(overrides)
    return data


class VariantIndexGroupingTest(unittest.TestCase):
    def test_store_digit_edition_lands_in_base_bucket_and_folds(self):
        # 7net edition (7usba071/7USBA-071) must share a bucket with the base
        # code, otherwise the group-level adoption never sees both sides and
        # the index would disagree with the full-collection actress view.
        rows = [
            row(),
            row(content_id="7usba071", dvd_id="7USBA-071"),
            row(content_id="usba00071", dvd_id=None, service_code="digital", runtime_mins=109),
        ]

        groups = build_variant_index_groups(rows)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["canonical_code"], "USBA-71")
        self.assertEqual(groups[0]["group_count"], 3)

    def test_bucket_key_strips_single_leading_digit(self):
        self.assertEqual(_bucket_key("7UMSO-533"), "UMSO-533")
        self.assertEqual(_bucket_key("USBA-71"), "USBA-71")
        # Genuine digit-prefixed families share a bucket with their stripped
        # form, but canonical equality inside the cluster step keeps distinct
        # works apart, so this is just a bucket key.
        self.assertEqual(_bucket_key("3DSVR-609"), "DSVR-609")

    def test_unrelated_titles_in_shared_bucket_stay_apart(self):
        rows = [
            row(content_id="umso533", dvd_id="UMSO-533", title_ja="完全に別の作品タイトルA", runtime_mins=120),
            row(content_id="7umso533", dvd_id="7UMSO-533", title_ja="別内容の格安版コンピレーション", runtime_mins=240, release_date="2020-05-05"),
        ]

        groups = build_variant_index_groups(rows)

        # No multi-item group should be produced.
        self.assertEqual(groups, [])


if __name__ == "__main__":
    unittest.main()
