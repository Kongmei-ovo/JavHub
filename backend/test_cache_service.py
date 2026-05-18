import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from services import cache


class CacheServiceTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "cache.sqlite3"
        self.patch = patch.object(cache, "_db_path", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tempdir.cleanup()

    def test_video_cache_round_trips_json_without_pickle(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"}, ttl=60)

        self.assertEqual(cache.get_video("abc-123"), {"content_id": "ABC-123"})

    def test_expired_items_are_removed(self):
        cache.set_search({"q": "abc"}, 1, {"data": []}, ttl=0)
        time.sleep(0.01)

        self.assertIsNone(cache.get_search({"q": "abc"}, 1))

    def test_purge_video_cache_removes_video_and_search_only(self):
        cache.set_video("abc-123", {"content_id": "ABC-123"})
        cache.set_search({"q": "abc"}, 1, {"data": []})
        cache.set_enum_list("makers", [{"id": 1}])

        self.assertEqual(cache.purge_video_cache(), 2)
        self.assertIsNone(cache.get_video("abc-123"))
        self.assertIsNone(cache.get_search({"q": "abc"}, 1))
        self.assertEqual(cache.get_enum_list("makers"), [{"id": 1}])


if __name__ == "__main__":
    unittest.main()
