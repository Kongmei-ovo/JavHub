from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


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


class TelegramSearchHandlerTest(TempDbMixin, unittest.IsolatedAsyncioTestCase):
    async def test_search_handler_builds_caption_with_total_pages(self):
        from telegram_bot.handlers.search import search_handler

        update = MagicMock()
        update.message.reply_photo = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock(args=["SIVR-438"])
        info_client = MagicMock()
        info_client.search_videos = AsyncMock(return_value={
            "total_count": 4,
            "data": [{"content_id": "sivr00438", "dvd_id": "SIVR-438", "title_ja": "Title"}],
        })
        info_client.get_video = AsyncMock(return_value={
            "content_id": "sivr00438",
            "dvd_id": "SIVR-438",
            "title_ja": "Title",
            "jacket_thumb_url": "https://img.test/cover.jpg",
        })

        with patch("telegram_bot.handlers.search.get_info_client", return_value=info_client):
            await search_handler(update, context)

        update.message.reply_photo.assert_awaited_once()
        caption = update.message.reply_photo.await_args.kwargs["caption"]
        self.assertIn("[第1页/共2页]", caption)

    async def test_download_callback_creates_manual_candidate(self):
        from database import list_download_candidate_events, list_download_candidates
        from telegram_bot.handlers.search import _do_download

        query = MagicMock()
        query.edit_message_text = AsyncMock()

        await _do_download(query, "SIVR-438", "SIVR-438", 1)

        rows = list_download_candidates(source="telegram")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content_id"], "SIVR-438")
        events = list_download_candidate_events(rows[0]["id"])
        self.assertEqual(events[0]["action"], "upsert")
        query.edit_message_text.assert_awaited_once()
        self.assertIn("已加入下载候选", query.edit_message_text.await_args.kwargs["text"])
