from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.client import ASGIClient, create_router_test_client
from test_support.postgres import TempPostgresMixin


class FavoriteCollectionsRouterTest(TempPostgresMixin, unittest.TestCase):
    def _client(self) -> ASGIClient:
        from routers.favorites import router

        return create_router_test_client(router)

    def test_create_list_update_and_delete_collection(self):
        client = self._client()

        created = client.post(
            "/api/v1/favorites/collections",
            json={"name": "Watch Later", "description": "Queued videos"},
        )
        self.assertEqual(created.status_code, 200)
        body = created.json()
        self.assertEqual(body["name"], "Watch Later")
        self.assertEqual(body["description"], "Queued videos")
        self.assertIsInstance(body["id"], int)
        self.assertIn("created_at", body)

        listed = client.get("/api/v1/favorites/collections")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["name"] for item in listed.json()], ["Watch Later"])

        updated = client.put(
            f"/api/v1/favorites/collections/{body['id']}",
            json={"name": "Favorites", "description": None},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Favorites")
        self.assertIsNone(updated.json()["description"])

        deleted = client.delete(f"/api/v1/favorites/collections/{body['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"deleted": True})

        empty = client.get("/api/v1/favorites/collections")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json(), [])

    def test_rejects_duplicate_collection_names(self):
        client = self._client()

        first = client.post("/api/v1/favorites/collections", json={"name": "Duplicates"})
        self.assertEqual(first.status_code, 200)

        duplicate = client.post("/api/v1/favorites/collections", json={"name": "Duplicates"})

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["detail"], "Collection name already exists")

    def test_rejects_empty_collection_names(self):
        client = self._client()

        response = client.post("/api/v1/favorites/collections", json={"name": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Collection name must not be empty")

    def test_update_rejects_duplicate_collection_names(self):
        client = self._client()
        first = client.post("/api/v1/favorites/collections", json={"name": "First"}).json()
        client.post("/api/v1/favorites/collections", json={"name": "Second"})

        duplicate = client.put(
            f"/api/v1/favorites/collections/{first['id']}",
            json={"name": "Second"},
        )

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["detail"], "Collection name already exists")

    def test_favorite_videos_include_indexed_variant_metadata_without_collapsing_favorites(self):
        from database import favorite
        from database.video_variant_index import replace_variant_groups

        favorite.toggle_favorite(
            "video",
            "miaa784::mono",
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "service_code": "mono"},
        )
        favorite.toggle_favorite(
            "video",
            "miaa00784::digital",
            {"content_id": "miaa00784", "dvd_id": None, "service_code": "digital"},
        )
        replace_variant_groups(
            [
                {
                    "group_id": "vg:miaa784",
                    "canonical_code": "MIAA-784",
                    "primary_content_id": "miaa784",
                    "group_count": 2,
                    "confidence": "high",
                    "items": [
                        {"content_id": "miaa784", "dvd_id": "MIAA-784", "display_code": "MIAA-784", "service_code": "mono", "variant_labels": [], "sort_rank": 0},
                        {"content_id": "miaa00784", "dvd_id": None, "display_code": "MIAA-784", "service_code": "digital", "variant_labels": [{"key": "digital", "label": "数字版", "short_label": "数字"}], "sort_rank": 1},
                    ],
                }
            ]
        )

        info_client = AsyncMock()
        info_client.get_video.side_effect = [
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "Mono", "service_code": "mono"},
            {"content_id": "miaa00784", "dvd_id": None, "title_ja": "Digital", "service_code": "digital"},
        ]
        translator = AsyncMock()
        translator.translate_video.side_effect = lambda _content_id, data, **_kwargs: data

        with patch("routers.favorites.get_info_client", return_value=info_client), \
             patch("routers.favorites.get_translator_service", return_value=translator):
            response = self._client().get("/api/v1/favorites/videos")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 2)
        self.assertEqual({item["content_id"] for item in body}, {"miaa784", "miaa00784"})
        self.assertTrue(all(item.get("variant_indexed") for item in body))
        self.assertEqual({item["variant_group_count"] for item in body}, {2})
        self.assertTrue(all(len(item.get("variant_group_items") or []) == 2 for item in body))


class FavoriteListRouteCacheTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_get_favorites_defaults_to_lightweight_index_cache_with_bypass(self):
        from routers import favorites

        with patch.object(favorites.favorite, "list_favorite_index", side_effect=[
            [{"entity_id": "first"}],
            [{"entity_id": "fresh"}],
        ]) as list_favorite_index, patch.object(favorites.favorite, "list_favorites") as list_favorites:
            first = await favorites.get_favorites()
            second = await favorites.get_favorites()
            bypassed = await favorites.get_favorites(cache_control="0")

        self.assertEqual(list_favorite_index.call_count, 2)
        list_favorites.assert_not_called()
        self.assertEqual(first[0]["entity_id"], "first")
        self.assertNotIn("metadata", first[0])
        self.assertEqual(second[0]["entity_id"], "first")
        self.assertEqual(bypassed[0]["entity_id"], "fresh")

    async def test_get_favorites_can_include_metadata_for_curated_page(self):
        from routers import favorites

        full_item = {"entity_id": "full", "metadata": {"title": "large"}}
        with patch.object(favorites.favorite, "list_favorites", return_value=[full_item]) as list_favorites, \
            patch.object(favorites.favorite, "list_favorite_index") as list_favorite_index:
            response = await favorites.get_favorites(include_metadata=True)

        list_favorites.assert_called_once_with(None)
        list_favorite_index.assert_not_called()
        self.assertEqual(response, [full_item])

    async def test_get_favorite_videos_uses_short_response_cache_with_bypass(self):
        from routers import favorites

        item = {
            "entity_id": "miaa784::mono",
            "metadata": {"content_id": "miaa784", "service_code": "mono"},
            "created_at": "2026-05-28 00:00:00",
        }
        info_client = AsyncMock()
        info_client.get_video.side_effect = [
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "cached"},
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "fresh"},
            {"content_id": "miaa784", "dvd_id": "MIAA-784", "title_ja": "uncached"},
        ]
        translator = AsyncMock()
        translator.translate_video.side_effect = lambda _content_id, data, **_kwargs: data

        with patch.object(favorites.favorite, "list_favorites", return_value=[item]) as list_favorites, \
            patch.object(favorites, "get_info_client", return_value=info_client), \
            patch.object(favorites, "get_translator_service", return_value=translator):
            first = await favorites.get_favorite_videos()
            second = await favorites.get_favorite_videos()
            bypassed = await favorites.get_favorite_videos(cache_control="0")

        self.assertEqual(list_favorites.call_count, 2)
        self.assertEqual(info_client.get_video.await_count, 2)
        self.assertEqual(first[0]["title_ja"], "cached")
        self.assertEqual(second[0]["title_ja"], "cached")
        self.assertEqual(bypassed[0]["title_ja"], "fresh")

    async def test_get_favorite_videos_page_enriches_only_requested_rows(self):
        from routers import favorites

        page = {
            "data": [
                {
                    "entity_id": "first::mono",
                    "metadata": {"content_id": "first", "service_code": "mono"},
                    "created_at": "2026-05-28 02:00:00",
                },
                {
                    "entity_id": "second::digital",
                    "metadata": {"content_id": "second", "service_code": "digital"},
                    "created_at": "2026-05-28 01:00:00",
                },
            ],
            "total": 25,
            "limit": 2,
            "offset": 10,
        }
        info_client = AsyncMock()
        info_client.get_video.side_effect = [
            {"content_id": "first", "dvd_id": "FIRST-001", "title_ja": "First"},
            {"content_id": "second", "dvd_id": "SECOND-001", "title_ja": "Second"},
        ]
        translator = AsyncMock()
        translator.translate_video.side_effect = lambda _content_id, data, **_kwargs: data

        with patch.object(favorites.favorite, "list_favorites_page", return_value=page) as list_page, \
            patch.object(favorites.favorite, "list_favorites") as list_all, \
            patch.object(favorites, "get_info_client", return_value=info_client), \
            patch.object(favorites, "get_translator_service", return_value=translator):
            response = await favorites.get_favorite_videos_page(limit=2, offset=10, cache_control="0")

        list_page.assert_called_once_with("video", limit=2, offset=10, include_metadata=True)
        list_all.assert_not_called()
        self.assertEqual(info_client.get_video.await_count, 2)
        self.assertEqual(response["total"], 25)
        self.assertEqual(response["limit"], 2)
        self.assertEqual(response["offset"], 10)
        self.assertTrue(response["has_more"])
        self.assertEqual([item["content_id"] for item in response["data"]], ["first", "second"])


class FavoriteCollectionsDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_list_favorite_index_omits_metadata_json_for_global_state(self):
        from database import favorite
        from database.base import get_db

        large_metadata = {"title": "Large", "blob": "x" * 20_000}
        favorite.toggle_favorite("video", "MIAA-784::mono", large_metadata)
        favorite.toggle_favorite("actress", "123", {"name_kanji": "Actor"})

        index_items = favorite.list_favorite_index()

        self.assertEqual(len(index_items), 2)
        self.assertTrue(all("metadata" not in item for item in index_items))
        self.assertTrue(all("metadata_json" not in item for item in index_items))
        self.assertEqual({item["entity_type"] for item in index_items}, {"video", "actress"})
        self.assertTrue(all("created_at" in item for item in index_items))

        with get_db() as conn:
            plan_rows = conn.execute(
                "EXPLAIN (FORMAT TEXT) SELECT entity_type, entity_id, created_at FROM favorites ORDER BY created_at DESC"
            ).fetchall()
        plan_text = "\n".join(row["QUERY PLAN"] for row in plan_rows)
        self.assertNotIn("metadata_json", plan_text)

    def test_list_favorites_page_bounds_metadata_rows_for_video_paging(self):
        from database import favorite
        from database.base import get_db

        with get_db() as conn:
            for index in range(4):
                conn.execute(
                    """
                    INSERT INTO favorites (entity_type, entity_id, metadata_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        "video",
                        f"ITEM-{index}::mono",
                        '{"content_id":"ITEM-%d","service_code":"mono"}' % index,
                        f"2026-05-28 00:0{index}:00+00",
                    ),
                )

        page = favorite.list_favorites_page("video", limit=2, offset=1, include_metadata=True)

        self.assertEqual(page["total"], 4)
        self.assertEqual(page["limit"], 2)
        self.assertEqual(page["offset"], 1)
        self.assertEqual(len(page["data"]), 2)
        self.assertTrue(all("metadata" in item for item in page["data"]))
        self.assertTrue(all("metadata_json" not in item for item in page["data"]))

    def test_cleanup_removes_legacy_video_favorites(self):
        from database import favorite
        from database.base import get_db

        favorite.toggle_favorite(
            "video",
            "MIAA-784",
            {"content_id": "MIAA-784", "dvd_id": "MIAA-784", "service_code": "mono"},
        )
        favorite.toggle_favorite(
            "video",
            "JUQ-001::digital",
            {"content_id": "JUQ-001", "dvd_id": "JUQ-001", "service_code": "digital"},
        )
        favorite.toggle_favorite("actress", "123", {"name_kanji": "Actor"})

        removed = favorite.cleanup_legacy_video_favorites()

        self.assertEqual(removed, 1)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT entity_type, entity_id FROM favorites ORDER BY entity_type, entity_id"
            ).fetchall()
        self.assertEqual(
            [(row["entity_type"], row["entity_id"]) for row in rows],
            [("actress", "123"), ("video", "JUQ-001::digital")],
        )

    def test_delete_collection_removes_collection_items(self):
        from database import favorite
        from database.base import get_db

        collection = favorite.create_collection("To Clean")
        with get_db() as conn:
            conn.execute(
                "INSERT INTO collection_items (collection_id, entity_type, entity_id) VALUES (?, ?, ?)",
                (collection["id"], "video", "MIAA-784"),
            )

        self.assertTrue(favorite.delete_collection(collection["id"]))

        with get_db() as conn:
            rows = conn.execute("SELECT * FROM collection_items").fetchall()
        self.assertEqual(rows, [])

    def test_list_favorites_tolerates_invalid_metadata_json(self):
        from database import favorite
        from database.base import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT INTO favorites (entity_type, entity_id, metadata_json) VALUES (?, ?, ?)",
                ("video", "BROKEN-001::mono", "{invalid json"),
            )
            conn.execute(
                "INSERT INTO favorites (entity_type, entity_id, metadata_json) VALUES (?, ?, ?)",
                ("video", "GOOD-001::mono", '{"service_code": "mono", "title": "Good"}'),
            )

        favorites = favorite.list_favorites("video")

        by_id = {item["entity_id"]: item for item in favorites}
        self.assertEqual(by_id["BROKEN-001::mono"]["metadata"], {})
        self.assertEqual(by_id["BROKEN-001::mono"]["entity_type"], "video")
        self.assertIn("created_at", by_id["BROKEN-001::mono"])
        self.assertEqual(
            by_id["GOOD-001::mono"]["metadata"],
            {"service_code": "mono", "title": "Good"},
        )


if __name__ == "__main__":
    unittest.main()
