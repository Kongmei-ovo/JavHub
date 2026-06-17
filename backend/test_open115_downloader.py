from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class Open115PathTests(unittest.TestCase):
    def test_item_id_directory_encoding_is_url_safe_and_reversible(self):
        from services.open115_downloader import decode_movie_directory, encode_movie_directory

        movie_id = "dmm:mono/abc 123?variant=1"
        encoded = encode_movie_directory(movie_id)

        self.assertNotIn("/", encoded)
        self.assertNotIn("?", encoded)
        self.assertEqual(decode_movie_directory(encoded), movie_id)


class Open115SubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_uses_only_item_id_directory(self):
        from services.open115_downloader import Open115DownloaderClient, encode_movie_directory

        client = AsyncMock()
        client.root_path = "/JavHub"
        client.ensure_folder_path.return_value = "folder-42"
        client.add_offline_task.return_value = ["abcdef"]
        downloader = Open115DownloaderClient(client=client)

        result = await downloader.submit("dmm:abc123", "magnet:?xt=urn:btih:abcdef")

        expected_path = f"/JavHub/{encode_movie_directory('dmm:abc123')}"
        client.ensure_folder_path.assert_awaited_once_with(expected_path)
        client.add_offline_task.assert_awaited_once_with(
            ["magnet:?xt=urn:btih:abcdef"],
            "folder-42",
        )
        self.assertEqual(result.folder_id, "folder-42")
        self.assertEqual(result.info_hash, "abcdef")
        self.assertEqual(result.path, expected_path)


class Open115FinalizerTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_finalizer_registers_all_videos_largest_default_and_subtitles_idempotently(self):
        from database import list_movie_resources
        from services.open115 import Open115File
        from services.open115_downloader import Open115DownloaderClient

        files = [
            Open115File("video-small", "folder", "part-a.mp4", "pick-a", False, 100, 1000, "mp4"),
            Open115File("video-large", "folder", "part-b.mkv", "pick-b", False, 900, 2000, "mkv"),
            Open115File("subtitle", "folder", "part-b.zh.ass", "pick-sub", False, 2, 0, "ass"),
            Open115File("image", "folder", "cover.jpg", "pick-image", False, 4, 0, "jpg"),
        ]

        class FakeClient:
            async def walk_files(self, file_id):
                self.walked_file_id = file_id
                for item in files:
                    yield item

        fake = FakeClient()
        downloader = Open115DownloaderClient(client=fake)

        with patch("modules.info_client.get_info_client", create=True) as info_client:
            first = await downloader.finalize(
                task_id=77,
                movie_id="stable:item-1",
                result_file_id="result-folder",
            )
            second = await downloader.finalize(
                task_id=77,
                movie_id="stable:item-1",
                result_file_id="result-folder",
            )

        rows = list_movie_resources("stable:item-1")
        videos = [row for row in rows if row["resource_type"] == "video"]
        subtitles = [row for row in rows if row["resource_type"] == "subtitle"]

        self.assertEqual(first["video_count"], 2)
        self.assertEqual(second["video_count"], 2)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(videos), 2)
        self.assertEqual(len(subtitles), 1)
        self.assertEqual([row["remote_file_id"] for row in videos if row["is_default"]], ["video-large"])
        self.assertEqual(subtitles[0]["related_resource_id"], next(
            row["id"] for row in videos if row["remote_file_id"] == "video-large"
        ))
        self.assertEqual(fake.walked_file_id, "result-folder")
        info_client.assert_not_called()

    async def test_video_without_pick_code_is_recorded_missing_not_default(self):
        from database import list_movie_resources
        from services.open115 import Open115File
        from services.open115_downloader import Open115DownloaderClient, Open115FinalizationError

        class FakeClient:
            async def walk_files(self, _file_id):
                yield Open115File("video-1", "folder", "movie.mp4", "", False, 100, 1000, "mp4")

        downloader = Open115DownloaderClient(client=FakeClient())

        with self.assertRaises(Open115FinalizationError):
            await downloader.finalize(task_id=1, movie_id="movie-1", result_file_id="file-1")

        rows = list_movie_resources("movie-1")
        self.assertEqual(rows[0]["status"], "missing")
        self.assertFalse(rows[0]["is_default"])


class Open115DownloaderServiceTests(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_create_task_persists_movie_binding_and_remote_folder(self):
        from database import get_download_task
        from services.downloader import downloader_service
        from services.open115_downloader import Open115Submission

        cfg = {
            "id": "open115",
            "type": "open115",
            "name": "115 Open",
            "enabled": True,
        }
        submission = Open115Submission(
            info_hash="hash-1",
            folder_id="folder-1",
            path="/JavHub/encoded",
        )

        with patch("services.downloader.get_downloader_config", return_value=cfg), \
             patch("services.downloader.open115_downloader.submit", new=AsyncMock(return_value=submission)):
            task_id = await downloader_service.create_download_task(
                "stable:item-1",
                "Movie",
                "magnet:?xt=urn:btih:hash-1",
            )

        task = get_download_task(task_id)
        self.assertEqual(task["movie_id"], "stable:item-1")
        self.assertEqual(task["content_id"], "stable:item-1")
        self.assertEqual(task["target_folder_id"], "folder-1")
        self.assertEqual(task["info_hash"], "hash-1")
        self.assertEqual(task["open115_task_id"], "hash-1")
        self.assertEqual(task["path"], "/JavHub/encoded")
        self.assertEqual(task["status"], "downloading")

    async def test_completed_open115_task_finalizes_without_scanner(self):
        from database import create_download_task, get_download_task, update_task_status
        from services.downloader import downloader_service

        task_id = create_download_task(
            "stable:item-1",
            "Movie",
            "magnet:?xt=urn:btih:hash-1",
            downloader_id="open115",
            downloader_name="115 Open",
            downloader_type="open115",
            movie_id="stable:item-1",
        )
        update_task_status(
            task_id,
            "downloading",
            info_hash="hash-1",
            target_folder_id="folder-1",
            open115_task_id="hash-1",
        )
        remote = {
            "info_hash": "hash-1",
            "status": 2,
            "file_id": "result-folder",
            "wp_path_id": "folder-1",
        }

        with patch("services.downloader.open115_downloader.find_task", new=AsyncMock(return_value=remote)), \
             patch("services.downloader.open115_downloader.finalize", new=AsyncMock(return_value={"video_count": 1})) as finalize:
            result = await downloader_service.poll_task_status(task_id)

        task = get_download_task(task_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["result_file_id"], "result-folder")
        finalize.assert_awaited_once_with(
            task_id=task_id,
            movie_id="stable:item-1",
            result_file_id="result-folder",
        )


    async def test_raw_offline_task_completes_without_finalize(self):
        from database import create_download_task, get_download_task, update_task_status
        from services.downloader import downloader_service

        task_id = create_download_task(
            "hash-raw",
            "Some Release",
            "magnet:?xt=urn:btih:hash-raw",
            downloader_id="open115",
            downloader_name="115 Open（原生）",
            downloader_type="open115",
            movie_id="hash-raw",
            kind="offline",
        )
        update_task_status(task_id, "downloading", info_hash="hash-raw", target_folder_id="42")
        remote = {"info_hash": "hash-raw", "status": 2, "file_id": "landed-folder"}

        with patch("services.downloader.open115_downloader.find_task", new=AsyncMock(return_value=remote)), \
             patch("services.downloader.open115_downloader.finalize", new=AsyncMock()) as finalize:
            result = await downloader_service.poll_task_status(task_id)

        task = get_download_task(task_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["result_file_id"], "landed-folder")
        finalize.assert_not_awaited()

    async def test_not_ready_keeps_task_finalizing_instead_of_failing(self):
        from database import create_download_task, get_download_task, update_task_status
        from services.downloader import downloader_service
        from services.open115_downloader import Open115NotReadyError

        task_id = create_download_task(
            "stable:item-2",
            "Movie",
            "magnet:?xt=urn:btih:hash-2",
            downloader_id="open115",
            downloader_name="115 Open",
            downloader_type="open115",
            movie_id="stable:item-2",
        )
        update_task_status(task_id, "downloading", info_hash="hash-2", target_folder_id="folder-2")
        remote = {"info_hash": "hash-2", "status": 2, "file_id": "result-folder"}

        with patch("services.downloader.open115_downloader.find_task", new=AsyncMock(return_value=remote)), \
             patch("services.downloader.open115_downloader.finalize",
                   new=AsyncMock(side_effect=Open115NotReadyError("not ready"))):
            result = await downloader_service.poll_task_status(task_id)

        task = get_download_task(task_id)
        self.assertEqual(result["status"], "finalizing")
        self.assertEqual(task["status"], "finalizing")
        self.assertNotEqual(task["status"], "failed")

    async def test_create_open115_offline_tasks_registers_tracked_offline_tasks(self):
        from database import get_download_task
        from services.downloader import downloader_service

        with patch("services.open115.open115_client.add_offline_task",
                   new=AsyncMock(side_effect=[["hash-1"], ["hash-2"]])) as add:
            result = await downloader_service.create_open115_offline_tasks(
                ["magnet:?xt=urn:btih:hash-1&dn=First+Movie", "magnet:?xt=urn:btih:hash-2"],
                "55",
            )

        self.assertEqual(len(result["added"]), 2)
        self.assertEqual(result["skipped"], [])
        # each link added individually, into the browsed folder
        self.assertEqual(add.await_count, 2)
        for call in add.await_args_list:
            self.assertEqual(call.args[1], "55")

        first = get_download_task(result["added"][0]["task_id"])
        self.assertEqual(first["kind"], "offline")
        self.assertEqual(first["downloader_type"], "open115")
        self.assertEqual(first["info_hash"], "hash-1")
        self.assertEqual(first["target_folder_id"], "55")
        self.assertEqual(first["status"], "downloading")
        self.assertEqual(first["title"], "First Movie")

    async def test_create_open115_offline_tasks_isolates_rejected_links(self):
        from services.downloader import downloader_service
        from services.open115 import Open115Error

        with patch("services.open115.open115_client.add_offline_task",
                   new=AsyncMock(side_effect=[Open115Error(None, "配额不足"), ["hash-ok"]])):
            result = await downloader_service.create_open115_offline_tasks(
                ["magnet:?xt=urn:btih:bad", "magnet:?xt=urn:btih:hash-ok"],
                "0",
            )

        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["reason"], "配额不足")


if __name__ == "__main__":
    unittest.main()
