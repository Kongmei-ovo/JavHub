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


class FavoriteCollectionsDatabaseTest(TempPostgresMixin, unittest.TestCase):
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
