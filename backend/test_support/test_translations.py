from __future__ import annotations

import unittest

from test_support.translations import noop_entity_translator, passthrough_video_translator


class TranslationTestSupportTest(unittest.IsolatedAsyncioTestCase):
    async def test_passthrough_video_translator_returns_original_items(self):
        translator = passthrough_video_translator()
        items = [{"content_id": "miaa784"}]

        result = await translator.translate_videos(items, allow_network=False)

        self.assertIs(result, items)
        translator.translate_videos.assert_awaited_once_with(items, allow_network=False)

    async def test_noop_entity_translator_records_entity_calls(self):
        translator = noop_entity_translator()
        items = [{"id": 1}]

        result = await translator.translate_entities(items, entity_type="label")

        self.assertIsNone(result)
        translator.translate_entities.assert_awaited_once_with(items, entity_type="label")
