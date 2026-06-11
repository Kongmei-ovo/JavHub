"""Variant-group favorite toggle tests (index + db stubbed, no postgres)."""
from __future__ import annotations

import sys
import types
import unittest
from unittest import mock


def _install_variant_index_stub(group):
    module = types.ModuleType("database.video_variant_index")
    module.get_variant_group_by_content_ids = lambda content_ids: (
        {cid: group for cid in content_ids} if group else {}
    )
    sys.modules["database.video_variant_index"] = module
    return module


GROUP = {
    "group_id": "vg:jums39:abc",
    "canonical_code": "JUMS-39",
    "group_count": 2,
    "items": [
        {"content_id": "jums039", "dvd_id": "JUMS-039", "service_code": "mono"},
        {"content_id": "4jums039", "dvd_id": "4JUMS039", "service_code": "rental"},
    ],
}


class FavoriteGroupToggleTest(unittest.TestCase):
    def setUp(self):
        from routers import favorites as favorites_router

        self.router = favorites_router
        self.store: dict[str, dict] = {}

        def set_favorite(entity_type, entity_id, metadata=None, favorited=True):
            key = f"{entity_type}|{entity_id}"
            if favorited:
                existed = key in self.store
                self.store.setdefault(key, metadata or {})
                return not existed
            return self.store.pop(key, None) is not None

        def is_favorite(entity_type, entity_id):
            return f"{entity_type}|{entity_id}" in self.store

        self.patches = [
            mock.patch.object(self.router.favorite, "set_favorite", set_favorite),
            mock.patch.object(self.router.favorite, "is_favorite", is_favorite),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        sys.modules.pop("database.video_variant_index", None)

    def _toggle(self, entity_id, metadata=None):
        req = self.router.ToggleFavoriteRequest(
            entity_type="video", entity_id=entity_id, metadata=metadata
        )
        return self.router.toggle_favorite(req)

    def test_favoriting_one_version_favorites_whole_group(self):
        _install_variant_index_stub(GROUP)
        result = self._toggle("jums039::mono", {"content_id": "jums039"})
        self.assertTrue(result["is_favorited"])
        self.assertEqual(result["group_size"], 2)
        self.assertIn("video|jums039::mono", self.store)
        self.assertIn("video|4jums039::rental", self.store)
        meta = self.store["video|4jums039::rental"]
        self.assertEqual(meta["canonical_code"], "JUMS-39")
        self.assertEqual(meta["variant_group_id"], "vg:jums39:abc")

    def test_toggling_any_version_unfavorites_whole_group(self):
        _install_variant_index_stub(GROUP)
        self._toggle("jums039::mono")
        result = self._toggle("4jums039::rental")
        self.assertFalse(result["is_favorited"])
        self.assertEqual(self.store, {})

    def test_partially_favorited_group_converges_to_all_on(self):
        _install_variant_index_stub(GROUP)
        # Pre-existing single favorite (legacy row)
        self.store["video|jums039::mono"] = {}
        result = self._toggle("4jums039::rental")
        # One member already on → toggle turns the WHOLE group off.
        self.assertFalse(result["is_favorited"])
        self.assertEqual(self.store, {})

    def test_video_without_indexed_group_falls_back_to_single_toggle(self):
        _install_variant_index_stub(None)
        toggled = {}

        def single_toggle(entity_type, entity_id, metadata=None):
            toggled["args"] = (entity_type, entity_id)
            return True

        with mock.patch.object(self.router.favorite, "toggle_favorite", single_toggle):
            result = self._toggle("solo001::mono")
        self.assertTrue(result["is_favorited"])
        self.assertEqual(toggled["args"], ("video", "solo001::mono"))


if __name__ == "__main__":
    unittest.main()
