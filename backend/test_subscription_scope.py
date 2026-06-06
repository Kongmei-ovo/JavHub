from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from test_support.postgres import TempPostgresMixin


class SubscriptionScopeDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_actress_subscription_keeps_backward_compatible_scope_fields(self):
        from database import add_subscription, get_subscriptions

        add_subscription(101, "Actor")

        row = get_subscriptions()[0]
        self.assertEqual(row["scope"], "actress")
        self.assertEqual(row["target_id"], 101)
        self.assertEqual(row["target_label"], "Actor")
        self.assertEqual(row["actress_id"], 101)
        self.assertEqual(row["actress_name"], "Actor")

    def test_maker_subscription_can_be_created_without_actress_columns(self):
        from database import add_subscription, get_subscriptions

        add_subscription(scope="maker", target_id=123, target_label="FALENO")

        row = get_subscriptions()[0]
        self.assertEqual(row["scope"], "maker")
        self.assertEqual(row["target_id"], 123)
        self.assertEqual(row["target_label"], "FALENO")
        self.assertIsNone(row["actress_id"])
        self.assertEqual(row["actress_name"], "FALENO")


class SubscriptionScopeRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_subscription_accepts_maker_scope_payload(self):
        from routers.subscriptions import CreateSubscriptionRequest, create_subscription

        request = CreateSubscriptionRequest(scope="maker", target_id=123, target_label="FALENO")

        with patch("routers.subscriptions.add_subscription", return_value=7) as add_subscription:
            result = await create_subscription(request)

        self.assertEqual(result, {"id": 7, "status": "ok"})
        add_subscription.assert_called_once_with(
            actress_id=None,
            actress_name=None,
            auto_download=False,
            scope="maker",
            target_id=123,
            target_label="FALENO",
        )

    async def test_create_subscription_still_accepts_legacy_actress_payload(self):
        from routers.subscriptions import CreateSubscriptionRequest, create_subscription

        request = CreateSubscriptionRequest(actress_id=101, actress_name="Actor", auto_download=True)

        with patch("routers.subscriptions.add_subscription", return_value=8) as add_subscription:
            result = await create_subscription(request)

        self.assertEqual(result, {"id": 8, "status": "ok"})
        add_subscription.assert_called_once_with(
            actress_id=101,
            actress_name="Actor",
            auto_download=True,
            scope="actress",
            target_id=None,
            target_label=None,
        )

    async def test_create_subscription_rejects_unknown_scope(self):
        from routers.subscriptions import CreateSubscriptionRequest

        with self.assertRaises(ValidationError):
            CreateSubscriptionRequest(scope="keyword", target_id=1, target_label="bad")


class SubscriptionScopePipelineTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fetch_maker_videos_pages_through_search_results(self):
        from services.watchlist_pipeline import WatchlistPipeline

        info_client = AsyncMock()
        info_client.get_maker_videos.side_effect = [
            {"data": [{"content_id": "one"}], "total_pages": 2},
            {"data": [{"content_id": "two"}], "total_pages": 2},
        ]

        pipeline = WatchlistPipeline(info_client=info_client)
        videos = await pipeline.fetch_maker_videos(123, page_size=999)

        self.assertEqual([video["content_id"] for video in videos], ["one", "two"])
        info_client.get_maker_videos.assert_any_await(123, page=1, page_size=100)
        info_client.get_maker_videos.assert_any_await(123, page=2, page_size=100)

    async def test_generates_candidates_for_label_scope_with_target_metadata(self):
        from services.watchlist_pipeline import WatchlistPipeline

        info_client = AsyncMock()
        info_client.get_label_videos.return_value = {
            "data": [
                {
                    "content_id": "sivr438",
                    "dvd_id": "SIVR-438",
                    "title_ja": "Title",
                    "release_date": "2026-05-01",
                }
            ]
        }
        emby_client = AsyncMock()
        emby_client.check_exists.return_value = False

        pipeline = WatchlistPipeline(info_client=info_client, emby_client=emby_client)
        result = await pipeline.generate_candidates_for_label(456, "FALENO", "subscription")

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["new_movies_count"], 1)
        self.assertEqual(result["scope"], "label")
        self.assertEqual(result["target_id"], 456)
        self.assertEqual(result["target_label"], "FALENO")
        self.assertEqual(result["candidates"][0]["dvd_id"], "SIVR-438")
        info_client.get_label_videos.assert_awaited_once_with(456, page=1, page_size=100)


class SubscriptionScopeServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_check_report_dispatches_non_actress_scope(self):
        from services.subscription import check_all_subscriptions_report

        with patch("services.subscription.get_subscriptions", return_value=[
            {
                "id": 9,
                "enabled": True,
                "scope": "maker",
                "target_id": 123,
                "target_label": "FALENO",
                "last_seen_codes": [],
                "cadence_minutes": 0,
            }
        ]), patch("services.subscription.WatchlistPipeline") as pipeline_cls, \
            patch("services.subscription.update_last_check") as update_last_check:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_maker = AsyncMock(return_value={
                "checked": 1,
                "created": 1,
                "existing": 0,
                "skipped": 0,
                "skipped_exempt": 0,
                "in_library": 0,
                "candidate_count": 1,
                "new_movies": [{"dvd_id": "SIVR-438"}],
            })

            report = await check_all_subscriptions_report()

        pipeline.generate_candidates_for_maker.assert_awaited_once_with(
            target_id=123,
            target_label="FALENO",
            trigger_source="subscription",
            reason="subscription_check",
        )
        self.assertEqual(report["subscriptions_checked"], 1)
        self.assertEqual(report["results"][0]["scope"], "maker")
        self.assertEqual(report["results"][0]["target_id"], 123)
        self.assertEqual(report["results"][0]["target_label"], "FALENO")
        update_last_check.assert_called_once()


class InfoClientScopeWrapperTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_scope_video_wrappers_delegate_to_video_search_filters(self):
        from modules.info_client import InfoClient

        client = InfoClient()
        with patch.object(client, "search_videos", AsyncMock(return_value={"data": []})) as search:
            await client.get_maker_videos(123, page=2, page_size=50)
            await client.get_series_videos(456, page=3, page_size=40)
            await client.get_label_videos(789, page=4, page_size=30)

        search.assert_any_await(maker_id=123, page=2, page_size=50)
        search.assert_any_await(series_id=456, page=3, page_size=40)
        search.assert_any_await(label_id=789, page=4, page_size=30)


if __name__ == "__main__":
    unittest.main()
