"""Regression tests for the "Emby errors must not be treated as 'missing'" rule.

If lookup fails because Emby is down/slow/auth-broken, ``EmbyUnavailableError``
is raised and nothing is cached — otherwise a single Emby blip floods the
candidate queue with false positives and may trigger mass downloads.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from modules.emby_client import EmbyClient, EmbyUnavailableError


class EmbyLookupFailurePropagationTest(unittest.IsolatedAsyncioTestCase):
    async def test_network_error_raises_emby_unavailable_and_does_not_cache(self):
        client = EmbyClient("http://emby.test", "token")

        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.side_effect = httpx.ConnectError("connection refused")
            with self.assertRaises(EmbyUnavailableError):
                await client.lookup("ABC-123")
            self.assertNotIn("ABC-123", client._exists_cache)

            get_mock.side_effect = None
            get_mock.return_value = {"Items": [{"Id": "emby-1", "Name": "ABC-123"}]}
            result = await client.lookup("ABC-123")

        self.assertIsNotNone(result)
        self.assertEqual(get_mock.await_count, 2)

    async def test_check_exists_propagates_emby_unavailable(self):
        client = EmbyClient("http://emby.test", "token")
        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.side_effect = httpx.HTTPStatusError(
                "503",
                request=httpx.Request("GET", "http://emby.test/Items"),
                response=httpx.Response(503),
            )
            with self.assertRaises(EmbyUnavailableError):
                await client.check_exists("ABC-123")

    async def test_successful_not_found_still_caches(self):
        client = EmbyClient("http://emby.test", "token")
        with patch.object(client, "_get", new_callable=AsyncMock) as get_mock:
            get_mock.return_value = {"Items": []}
            self.assertIsNone(await client.lookup("ABC-123"))
            # 2nd call must come from the negative cache, not hit Emby again.
            self.assertIsNone(await client.lookup("abc-123"))

        get_mock.assert_awaited_once()


class WatchlistPipelineEmbyAbortTest(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_bails_after_repeated_emby_errors(self):
        from services.watchlist_pipeline import WatchlistPipeline

        emby = AsyncMock()
        emby.check_exists.side_effect = EmbyUnavailableError("boom")

        pipeline = WatchlistPipeline(emby_client=emby)
        videos = [
            {"content_id": f"AAA{idx:03d}", "dvd_id": f"AAA-{idx:03d}", "title_ja": "x"}
            for idx in range(5)
        ]

        with patch(
            "services.watchlist_pipeline.upsert_candidate_from_video",
            side_effect=AssertionError("must not write candidates when Emby is down"),
        ), patch(
            "services.watchlist_pipeline.download_candidate_content_keys",
            return_value=set(),
        ), patch(
            "services.watchlist_pipeline.is_video_exempt",
            return_value=False,
        ):
            result = await pipeline._generate_candidates_for_videos(
                videos,
                actress_id=1,
                actress_name="X",
                trigger_source="subscription",
                reason="test",
                emby_snapshot=None,
            )

        self.assertTrue(result.get("emby_unavailable"))
        self.assertEqual(result.get("created"), 0)
        # Should stop after the 3rd consecutive failure (counted via skipped)
        self.assertLessEqual(emby.check_exists.await_count, 5)


if __name__ == "__main__":
    unittest.main()
