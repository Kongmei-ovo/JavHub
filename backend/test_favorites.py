from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TempDbMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.base_patch = patch("database.base.DB_PATH", self.db_path)
        self.base_patch.start()

        from database import init_db

        init_db()

    def tearDown(self):
        self.base_patch.stop()
        self.tmp.cleanup()


class FavoriteCollectionsRouterTest(TempDbMixin, unittest.TestCase):
    def _client(self) -> TestClient:
        from routers.favorites import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

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


class FavoriteCollectionsDatabaseTest(TempDbMixin, unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
