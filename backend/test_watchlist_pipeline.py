from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

from test_support.postgres import TempPostgresMixin


class DownloadCandidateDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_candidate_upsert_dedupes_by_content_and_source(self):
        from database import list_download_candidates, upsert_download_candidate

        first = upsert_download_candidate(
            content_id="SIVR-438",
            title="First",
            actress_id=1,
            source="subscription",
        )
        second = upsert_download_candidate(
            content_id="SIVR-438",
            title="Second",
            actress_id=1,
            source="subscription",
        )

        rows = list_download_candidates(source="subscription")
        self.assertEqual(len(rows), 1)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(rows[0]["title"], "Second")

    def test_candidate_upsert_reports_real_insert_only_once(self):
        from database import upsert_download_candidate

        first = upsert_download_candidate(
            content_id="SIVR-438",
            title="First",
            source="supplement",
            return_insert_status=True,
        )
        second = upsert_download_candidate(
            content_id="SIVR-438",
            title="Second",
            source="supplement",
            return_insert_status=True,
        )

        self.assertTrue(first["was_inserted"])
        self.assertFalse(second["was_inserted"])
        self.assertEqual(first["id"], second["id"])

    def test_candidate_upsert_preserves_failed_status(self):
        from database import list_download_candidates, set_download_candidate_status, upsert_download_candidate

        candidate = upsert_download_candidate(content_id="SIVR-438", source="subscription")
        set_download_candidate_status(candidate["id"], "failed", error_msg="openlist timeout")

        refreshed = upsert_download_candidate(
            content_id="SIVR-438",
            title="Refreshed",
            source="subscription",
            status="candidate",
        )

        self.assertEqual(refreshed["status"], "failed")
        rows = list_download_candidates(source="subscription")
        self.assertEqual(rows[0]["status"], "failed")

    def test_download_candidate_content_keys_returns_lightweight_existing_set(self):
        from database import download_candidate_content_keys, upsert_download_candidate

        upsert_download_candidate(content_id="SIVR-438", source="subscription", actress_id=901)
        upsert_download_candidate(content_id="ABP-588", source="subscription", actress_id=901)
        upsert_download_candidate(content_id="MIAA-999", source="inventory", actress_id=901)
        upsert_download_candidate(content_id="SSIS-001", source="subscription", actress_id=902)

        keys = download_candidate_content_keys(actress_id=901, source="subscription")

        self.assertEqual(keys, {("SIVR-438", "subscription"), ("ABP-588", "subscription")})


class ActorMappingDatabaseTest(TempPostgresMixin, unittest.TestCase):
    def test_confirm_ignore_and_delete_mapping(self):
        from database import (
            confirm_actor_mapping,
            delete_actor_mapping,
            get_confirmed_actor_mapping,
            ignore_actor_mapping,
            list_actor_mappings,
        )

        mapping_id = confirm_actor_mapping("emby-1", "Emby Name", 123, "JavInfo Name")
        confirmed = get_confirmed_actor_mapping("emby-1")
        self.assertEqual(confirmed["javinfo_actress_id"], 123)
        self.assertEqual(confirmed["status"], "confirmed")

        ignore_actor_mapping("emby-2", "Ignored")
        ignore_actor_mapping("emby-2", "Ignored Again")
        ignored = list_actor_mappings(status="ignored")
        self.assertEqual(len(ignored), 1)
        self.assertEqual(ignored[0]["emby_actor_name"], "Ignored Again")

        self.assertTrue(delete_actor_mapping(mapping_id))
        self.assertIsNone(get_confirmed_actor_mapping("emby-1"))

    def test_candidate_upsert_does_not_overwrite_manual_decision(self):
        from database import confirm_actor_mapping, list_actor_mappings, upsert_actor_mapping

        confirm_actor_mapping("emby-1", "Emby Name", 123, "Jav Name")
        upsert_actor_mapping(
            "emby-1",
            "Emby Name",
            123,
            "Jav Name",
            confidence=0.6,
            status="candidate",
            source="name_match",
        )

        rows = list_actor_mappings(emby_actor_id="emby-1")
        self.assertEqual(rows[0]["status"], "confirmed")
        self.assertEqual(rows[0]["source"], "manual")

    def test_mapping_summary_counts_candidates(self):
        from database import mapping_summary, upsert_actor_mapping

        upsert_actor_mapping("emby-1", "Emby Name", 123, "Jav Name", status="candidate", source="name_match")
        summary = mapping_summary([{"actress_id": "emby-1"}, {"actress_id": "emby-2"}])

        self.assertEqual(summary["candidate"], 1)
        self.assertEqual(summary["unmapped"], 2)

    def test_mapping_summary_for_snapshot_counts_without_actor_rows(self):
        from database import (
            confirm_actor_mapping,
            create_snapshot_key,
            ignore_actor_mapping,
            mapping_summary_for_snapshot,
            save_emby_actors_snapshot,
            upsert_actor_mapping,
        )

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [
            {"actress_id": 901, "actress_name": "Mapped", "video_count": 3},
            {"actress_id": 902, "actress_name": "Ignored", "video_count": 2},
            {"actress_id": 903, "actress_name": "Candidate", "video_count": 1},
            {"actress_id": 904, "actress_name": "Open", "video_count": 1},
        ])
        confirm_actor_mapping("901", "Mapped", 1, "Mapped")
        ignore_actor_mapping("902", "Ignored")
        upsert_actor_mapping("903", "Candidate", 3, "Candidate", status="candidate", source="name_match")
        upsert_actor_mapping("999", "Other Snapshot", 9, "Other", status="candidate", source="name_match")

        summary = mapping_summary_for_snapshot(snapshot_key)

        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["confirmed"], 1)
        self.assertEqual(summary["ignored"], 1)
        self.assertEqual(summary["candidate"], 1)
        self.assertEqual(summary["unmapped"], 2)
        self.assertEqual(summary["coverage"], 0.25)

    def test_mapping_state_for_actor_ids_returns_lightweight_decisions_and_ignored_pairs(self):
        from database import (
            confirm_actor_mapping,
            ignore_actor_mapping,
            mapping_state_for_actor_ids,
            upsert_actor_mapping,
        )

        confirm_actor_mapping("901", "Confirmed", 1, "Confirmed")
        ignore_actor_mapping("902", "Ignored Actor")
        ignore_actor_mapping("903", "Ignored Pair", 3, "Ignored Pair")
        upsert_actor_mapping("904", "Candidate", 4, "Candidate", status="candidate", source="name_match")

        state = mapping_state_for_actor_ids(["901", "902", "903", "904", "999"])

        self.assertEqual(state["decided_actor_ids"], {"901", "902"})
        self.assertEqual(state["ignored_pairs"], {("903", 3)})


class InventoryDatabasePerformanceTest(TempPostgresMixin, unittest.TestCase):
    def test_missing_video_helpers_support_indexed_lookup_and_summary(self):
        from database import (
            add_missing_video,
            get_missing_video,
            list_missing_videos_page,
            missing_videos_summary,
            upsert_inventory_actor,
        )

        upsert_inventory_actor(901, "Actor A", primary_name="Primary A")
        upsert_inventory_actor(902, "Actor B")
        add_missing_video("A-001", 901, "A First", "2026-02-01", "a1.jpg")
        add_missing_video("A-002", 901, "A Second", "2026-03-01", "a2.jpg")
        add_missing_video("B-001", 902, "B First", "2026-01-01", "b1.jpg")

        one = get_missing_video("A-001")
        page = list_missing_videos_page(limit=2, offset=0)
        summary = missing_videos_summary(limit=2)

        self.assertEqual(one["title"], "A First")
        self.assertEqual(page["total"], 3)
        self.assertEqual([row["content_id"] for row in page["data"]], ["A-002", "A-001"])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["top_actresses"][0], {
            "actress_id": 901,
            "actress_name": "Primary A",
            "missing_count": 2,
        })


class ActorMappingCandidateTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_generate_name_match_candidates_for_unmapped_actor(self):
        from database import create_snapshot_key, list_actor_mappings, save_emby_actors_snapshot
        from services.actor_mapping_candidates import generate_actor_mapping_candidates

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 123, "name_kanji": "糸井瑠花", "movie_count": 99, "image_url": "itoi.jpg"},
                {"id": 456, "name_kanji": "別人", "movie_count": 1},
            ]
        }

        result = await generate_actor_mapping_candidates(info_client=info_client)
        rows = list_actor_mappings(status="candidate")

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["emby_actor_id"], "901")
        self.assertEqual(rows[0]["javinfo_actress_id"], 123)
        self.assertEqual(rows[0]["source"], "exact_review")
        self.assertEqual(rows[0]["javinfo_avatar_url"], "itoi.jpg")
        self.assertEqual(rows[0]["movie_count"], 99)
        self.assertIn("name_score", rows[0]["confidence_breakdown"])
        self.assertEqual(rows[0]["confidence_label"], "高置信")
        self.assertEqual(rows[0]["risk_flags"], [])
        self.assertEqual(result["candidates"][0]["javinfo_avatar_url"], "itoi.jpg")

    async def test_unmapped_api_groups_candidates_with_cached_ai_metadata(self):
        from database import create_snapshot_key, save_emby_actors_snapshot, update_actor_mapping_ai_review, upsert_actor_mapping
        from routers import inventory

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
            "image_tag": "emby-image",
        }])
        upsert_actor_mapping(
            "901",
            "糸井瑠花",
            123,
            "糸井瑠花",
            confidence=0.96,
            status="candidate",
            source="exact_review",
            javinfo_avatar_url="itoi.jpg",
            movie_count=99,
            confidence_breakdown={"name_score": 1.0, "signals": ["名称精确一致"]},
            confidence_label="高置信",
            risk_flags=[],
        )
        update_actor_mapping_ai_review("901", 123, "same_person", 0.94, "名称一致且作品数充足", "gpt-test")

        result = inventory.list_unmapped_actor_mappings()

        self.assertEqual(result["total"], 1)
        actor = result["data"][0]
        self.assertTrue(actor["avatar_url"].endswith("tag=emby-image"))
        self.assertEqual(actor["candidate_count"], 1)
        candidate = actor["candidates"][0]
        self.assertEqual(candidate["javinfo_avatar_url"], "itoi.jpg")
        self.assertEqual(candidate["movie_count"], 99)
        self.assertEqual(candidate["confidence_breakdown"]["name_score"], 1.0)
        self.assertEqual(candidate["confidence_label"], "高置信")
        self.assertEqual(candidate["ai_decision"], "same_person")
        self.assertEqual(candidate["ai_confidence"], 0.94)
        self.assertEqual(candidate["ai_reason"], "名称一致且作品数充足")

    async def test_mapping_search_returns_normalized_candidates(self):
        from services.actor_mapping_candidates import search_actor_mapping_candidates

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 123, "name_kanji": "糸井瑠花", "movie_count": 99, "image_url": "itoi.jpg"},
            ]
        }

        result = await search_actor_mapping_candidates("901", "糸井瑠花", q="瑠花", info_client=info_client)

        self.assertEqual(result["total"], 1)
        candidate = result["data"][0]
        self.assertEqual(candidate["emby_actor_id"], "901")
        self.assertEqual(candidate["javinfo_actress_id"], 123)
        self.assertEqual(candidate["javinfo_avatar_url"], "itoi.jpg")
        self.assertIn("name_score", candidate["confidence_breakdown"])

    async def test_ai_review_persists_without_confirming_mapping(self):
        from database import create_snapshot_key, list_actor_mappings, save_emby_actors_snapshot, upsert_actor_mapping
        from routers import inventory

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])
        upsert_actor_mapping(
            "901",
            "糸井瑠花",
            123,
            "糸井瑠花",
            confidence=0.96,
            status="candidate",
            source="exact_review",
        )

        with patch("services.actor_mapping_candidates.get_ai_client") as get_ai_client:
            client = AsyncMock()
            client.chat.return_value.content = '{"decision":"same_person","confidence":0.93,"reason":"名称一致"}'
            client.chat.return_value.model = "gemini-test"
            get_ai_client.return_value = client
            result = await inventory.ai_review_mapping(inventory.ActorMappingAiReviewRequest(
                emby_actor_id="901",
                emby_actor_name="糸井瑠花",
                javinfo_actress_id=123,
                javinfo_actress_name="糸井瑠花",
                confidence=0.96,
                source="exact_review",
            ))

        rows = list_actor_mappings(status="candidate")
        self.assertTrue(result["success"])
        self.assertEqual(result["ai_decision"], "same_person")
        self.assertEqual(rows[0]["status"], "candidate")
        self.assertEqual(rows[0]["ai_decision"], "same_person")
        self.assertEqual(rows[0]["ai_reason"], "名称一致")

    async def test_generate_candidates_skips_confirmed_actor(self):
        from database import (
            confirm_actor_mapping,
            create_snapshot_key,
            list_actor_mappings,
            save_emby_actors_snapshot,
        )
        from services.actor_mapping_candidates import generate_actor_mapping_candidates

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])
        confirm_actor_mapping("901", "糸井瑠花", 123, "糸井瑠花")

        info_client = AsyncMock()
        result = await generate_actor_mapping_candidates(info_client=info_client)

        self.assertEqual(result["checked"], 0)
        info_client.list_actresses.assert_not_called()
        self.assertEqual(len(list_actor_mappings(status="candidate")), 0)

    async def test_generate_candidates_pages_snapshot_until_limit(self):
        from services import actor_mapping_candidates

        calls = []
        state_calls = []

        def snapshot_page(snapshot_key, search=None, page=1, page_size=50, **_kwargs):
            calls.append({"snapshot_key": snapshot_key, "search": search, "page": page, "page_size": page_size})
            if page == 1:
                return {
                    "data": [
                        {"actress_id": 901, "actress_name": "A"},
                        {"actress_id": 902, "actress_name": "B"},
                    ],
                    "total_pages": 2,
                }
            return {
                "data": [{"actress_id": 903, "actress_name": "C"}],
                "total_pages": 2,
            }

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {"data": []}

        def mapping_state(actor_ids):
            state_calls.append(list(actor_ids))
            return {"decided_actor_ids": {"901"}, "ignored_pairs": set()}

        with patch.object(actor_mapping_candidates, "get_latest_snapshot_key", return_value="snap-1"), \
            patch.object(actor_mapping_candidates, "mapping_state_for_actor_ids", Mock(side_effect=mapping_state)), \
            patch.object(actor_mapping_candidates, "get_snapshot_actors", side_effect=snapshot_page), \
            patch.object(actor_mapping_candidates, "upsert_actor_mapping", side_effect=AssertionError("no candidates should be created")):
            result = await actor_mapping_candidates.generate_actor_mapping_candidates(
                search="actor",
                limit=2,
                info_client=info_client,
            )

        self.assertEqual(calls, [
            {"snapshot_key": "snap-1", "search": "actor", "page": 1, "page_size": 100},
            {"snapshot_key": "snap-1", "search": "actor", "page": 2, "page_size": 100},
        ])
        self.assertEqual(state_calls, [["901", "902"], ["903"]])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(info_client.list_actresses.await_count, 2)

    async def test_generate_candidates_keeps_actor_with_only_ignored_candidate_visible(self):
        from database import (
            create_snapshot_key,
            ignore_actor_mapping,
            list_actor_mappings,
            save_emby_actors_snapshot,
        )
        from routers import inventory

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])
        ignore_actor_mapping("901", "糸井瑠花", 456, "別人")

        result = inventory.list_unmapped_actor_mappings()

        self.assertEqual(len(list_actor_mappings(status="ignored")), 1)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["data"][0]["emby_actor_id"], "901")

    async def test_auto_match_confirms_exact_unique_candidate(self):
        from database import create_snapshot_key, get_confirmed_actor_mapping, list_actor_mappings, save_emby_actors_snapshot
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 123, "name_kanji": "糸井瑠花", "movie_count": 99},
                {"id": 456, "name_kanji": "糸井瑠", "movie_count": 80},
            ]
        }

        result = await auto_match_actor_mappings(info_client=info_client)
        confirmed = get_confirmed_actor_mapping("901")

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["auto_confirmed"], 1)
        self.assertEqual(result["candidates_created"], 0)
        self.assertEqual(confirmed["javinfo_actress_id"], 123)
        self.assertEqual(confirmed["source"], "auto_match")
        self.assertEqual(len(list_actor_mappings(status="candidate")), 0)

    async def test_auto_match_keeps_ambiguous_exact_candidates_for_review(self):
        from database import create_snapshot_key, list_actor_mappings, save_emby_actors_snapshot
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "Rio",
            "video_count": 12,
        }])

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 123, "name_romaji": "Rio", "movie_count": 99},
                {"id": 456, "name_en": "RIO", "movie_count": 80},
            ]
        }

        result = await auto_match_actor_mappings(info_client=info_client)
        rows = list_actor_mappings(status="candidate")

        self.assertEqual(result["auto_confirmed"], 0)
        self.assertEqual(result["ambiguous"], 1)
        self.assertEqual(result["candidates_created"], 2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["source"] == "exact_ambiguous" for row in rows))

    async def test_auto_match_does_not_confirm_similarity_only_match(self):
        from database import create_snapshot_key, list_actor_mappings, save_emby_actors_snapshot
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 123, "name_kanji": "糸井瑠花改", "movie_count": 99},
            ]
        }

        result = await auto_match_actor_mappings(info_client=info_client)
        rows = list_actor_mappings(status="candidate")

        self.assertEqual(result["auto_confirmed"], 0)
        self.assertEqual(result["candidates_created"], 1)
        self.assertEqual(rows[0]["status"], "candidate")
        self.assertEqual(rows[0]["source"], "contains_match")

    async def test_auto_match_respects_decisions_and_ignored_candidate(self):
        from database import (
            confirm_actor_mapping,
            create_snapshot_key,
            ignore_actor_mapping,
            list_actor_mappings,
            save_emby_actors_snapshot,
        )
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [
            {"actress_id": 901, "actress_name": "Confirmed", "video_count": 1},
            {"actress_id": 902, "actress_name": "IgnoredPair", "video_count": 1},
            {"actress_id": 903, "actress_name": "IgnoredActor", "video_count": 1},
        ])
        confirm_actor_mapping("901", "Confirmed", 1, "Confirmed")
        ignore_actor_mapping("902", "IgnoredPair", 2, "IgnoredPair")
        ignore_actor_mapping("903", "IgnoredActor")

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [
                {"id": 2, "name_kanji": "IgnoredPair", "movie_count": 9},
            ]
        }

        result = await auto_match_actor_mappings(info_client=info_client)
        rows = list_actor_mappings()

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["auto_confirmed"], 0)
        self.assertEqual(result["candidates_created"], 0)
        self.assertEqual(result["skipped"], 3)
        self.assertEqual(len([row for row in rows if row["status"] == "confirmed"]), 1)
        self.assertEqual(len([row for row in rows if row["status"] == "ignored"]), 2)

    async def test_auto_match_dry_run_does_not_write_database(self):
        from database import create_snapshot_key, list_actor_mappings, save_emby_actors_snapshot
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])
        info_client = AsyncMock()
        info_client.list_actresses.return_value = {
            "data": [{"id": 123, "name_kanji": "糸井瑠花", "movie_count": 99}]
        }

        result = await auto_match_actor_mappings(dry_run=True, info_client=info_client)

        self.assertEqual(result["auto_confirmed"], 1)
        self.assertEqual(len(list_actor_mappings()), 0)

    async def test_auto_match_collects_query_errors(self):
        from database import create_snapshot_key, save_emby_actors_snapshot
        from services.actor_mapping_candidates import auto_match_actor_mappings

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "糸井瑠花",
            "video_count": 12,
        }])
        info_client = AsyncMock()
        info_client.list_actresses.side_effect = RuntimeError("javinfo down")

        result = await auto_match_actor_mappings(info_client=info_client)

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["auto_confirmed"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("javinfo down", result["errors"][0]["error"])

    async def test_auto_match_pages_snapshot_until_limit(self):
        from services import actor_mapping_candidates

        calls = []
        state_calls = []

        def snapshot_page(snapshot_key, search=None, page=1, page_size=50, **_kwargs):
            calls.append({"snapshot_key": snapshot_key, "search": search, "page": page, "page_size": page_size})
            if page == 1:
                return {
                    "data": [
                        {"actress_id": 901, "actress_name": "A"},
                        {"actress_id": 902, "actress_name": "B"},
                    ],
                    "total_pages": 2,
                }
            return {
                "data": [{"actress_id": 903, "actress_name": "C"}],
                "total_pages": 2,
            }

        info_client = AsyncMock()
        info_client.list_actresses.return_value = {"data": []}

        def mapping_state(actor_ids):
            state_calls.append(list(actor_ids))
            return {"decided_actor_ids": {"901"}, "ignored_pairs": set()}

        with patch.object(actor_mapping_candidates, "get_latest_snapshot_key", return_value="snap-1"), \
            patch.object(actor_mapping_candidates, "mapping_state_for_actor_ids", Mock(side_effect=mapping_state)), \
            patch.object(actor_mapping_candidates, "get_snapshot_actors", side_effect=snapshot_page):
            result = await actor_mapping_candidates.auto_match_actor_mappings(
                search="actor",
                limit=2,
                info_client=info_client,
            )

        self.assertEqual(calls, [
            {"snapshot_key": "snap-1", "search": "actor", "page": 1, "page_size": 100},
            {"snapshot_key": "snap-1", "search": "actor", "page": 2, "page_size": 100},
        ])
        self.assertEqual(state_calls, [["901", "902"], ["903"]])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["skipped"], 3)
        self.assertEqual(info_client.list_actresses.await_count, 2)

    async def test_auto_match_clamps_unbounded_limit(self):
        from services import actor_mapping_candidates

        with patch.object(actor_mapping_candidates, "get_latest_snapshot_key", return_value=None):
            result = await actor_mapping_candidates.auto_match_actor_mappings(limit=100000)

        self.assertEqual(result["checked"], 0)
        self.assertEqual(result["limit"], 2000)


class WatchlistPipelineTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_subscription_pipeline_creates_candidate_for_missing_movie(self):
        from services.watchlist_pipeline import WatchlistPipeline

        info_client = AsyncMock()
        info_client.get_actress_videos.return_value = {
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
        result = await pipeline.generate_candidates_for_actress(1, "Actor", "subscription")

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["new_movies_count"], 1)
        self.assertEqual(result["candidates"][0]["dvd_id"], "SIVR-438")
        info_client.get_actress_videos.assert_awaited_once()
        self.assertEqual(info_client.get_actress_videos.await_args.kwargs["include_supplement"], "1")

    async def test_subscription_pipeline_uses_lightweight_candidate_key_lookup(self):
        from services import watchlist_pipeline

        info_client = AsyncMock()
        info_client.get_actress_videos.return_value = {
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

        with patch.object(
            watchlist_pipeline,
            "download_candidate_content_keys",
            Mock(return_value={("sivr438", "subscription")}),
        ) as key_lookup:
            pipeline = watchlist_pipeline.WatchlistPipeline(info_client=info_client, emby_client=emby_client)
            result = await pipeline.generate_candidates_for_actress(1, "Actor", "subscription")

        key_lookup.assert_called_once_with(actress_id=1, source="subscription")
        self.assertEqual(result["existing"], 1)


class SupplementCandidatePipelineTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_supplement_movies_create_download_candidates_for_missing_rows(self):
        from database import get_download_candidate, list_download_candidates
        from services.supplement_candidates import generate_download_candidates_from_supplement

        info_client = AsyncMock()
        info_client.proxy_get.return_value = {
            "data": [
                {
                    "id": 11,
                    "canonical_number": "SIVR438",
                    "dvd_id": "SIVR-438",
                    "title": "Supplement Only",
                    "release_date": "2026-05-01",
                    "local_actress_id": 123,
                    "actress_name": "Actor",
                },
                {
                    "id": 12,
                    "canonical_number": "ABP588",
                    "dvd_id": "ABP-588",
                    "title": "Already In Library",
                },
                {
                    "id": 13,
                    "canonical_number": "MIAA999",
                    "dvd_id": "MIAA-999",
                    "title": "Ignored",
                    "status": "manual_ignored",
                    "match_status": "manual_ignored",
                },
            ],
        }
        emby_client = AsyncMock()
        emby_client.check_exists.side_effect = lambda code: code == "ABP-588"

        result = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
            actress_id=123,
            actress_name="Actor",
        )

        rows = list_download_candidates(source="supplement")
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["in_library"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dvd_id"], "SIVR-438")
        self.assertEqual(rows[0]["reason"], "supplement_only")
        self.assertEqual(get_download_candidate(rows[0]["id"])["events"][0]["action"], "supplement_imported")
        info_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/movies",
            params={"page": 1, "page_size": 100, "matched": "false", "actress_id": 123},
        )

    async def test_supplement_candidate_import_counts_existing_candidates(self):
        from database import get_download_candidate, list_download_candidates
        from services.supplement_candidates import generate_download_candidates_from_supplement

        info_client = AsyncMock()
        info_client.proxy_get.return_value = {
            "data": [{
                "id": 11,
                "canonical_number": "SIVR438",
                "dvd_id": "SIVR-438",
                "title": "Supplement Only",
            }],
        }
        emby_client = AsyncMock()
        emby_client.check_exists.return_value = False

        first = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
        )
        second = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
        )

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["existing"], 1)
        rows = list_download_candidates(source="supplement")
        self.assertEqual(len(rows), 1)
        events = get_download_candidate(rows[0]["id"])["events"]
        self.assertEqual([event["action"] for event in events], ["supplement_imported"])

    async def test_supplement_candidate_import_uses_upsert_result_when_race_inserts_candidate(self):
        from database import get_download_candidate, list_download_candidates
        from services.supplement_candidates import generate_download_candidates_from_supplement

        info_client = AsyncMock()
        info_client.proxy_get.return_value = {
            "data": [{
                "id": 11,
                "canonical_number": "SIVR438",
                "dvd_id": "SIVR-438",
                "title": "Supplement Only",
            }],
        }
        emby_client = AsyncMock()

        async def insert_racing_candidate(_code):
            from database import upsert_download_candidate

            upsert_download_candidate(
                content_id="SIVR438",
                dvd_id="SIVR-438",
                title="Racing Request",
                source="supplement",
            )
            return False

        emby_client.check_exists.side_effect = insert_racing_candidate

        result = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
        )

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["existing"], 1)
        rows = list_download_candidates(source="supplement")
        self.assertEqual(len(rows), 1)
        events = get_download_candidate(rows[0]["id"])["events"]
        self.assertEqual(events, [])

    async def test_supplement_candidate_import_paginates_until_limit(self):
        from database import list_download_candidates
        from services.supplement_candidates import generate_download_candidates_from_supplement

        info_client = AsyncMock()
        pages = {
            1: {
                "data": [{
                    "id": 11,
                    "canonical_number": "SIVR438",
                    "dvd_id": "SIVR-438",
                    "title": "First Page",
                }],
                "total_pages": 2,
            },
            2: {
                "data": [{
                    "id": 12,
                    "canonical_number": "ABP588",
                    "dvd_id": "ABP-588",
                    "title": "Second Page",
                }],
                "total_pages": 2,
            },
        }
        info_client.proxy_get.side_effect = lambda _path, params: pages[params["page"]]
        emby_client = AsyncMock()
        emby_client.check_exists.return_value = False

        result = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
            limit=150,
        )

        rows = list_download_candidates(source="supplement")
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["created"], 2)
        self.assertEqual([row["dvd_id"] for row in rows], ["SIVR-438", "ABP-588"])
        self.assertEqual(
            [call.kwargs["params"] for call in info_client.proxy_get.await_args_list],
            [
                {"page": 1, "page_size": 100, "matched": "false"},
                {"page": 2, "page_size": 100, "matched": "false"},
            ],
        )

    async def test_supplement_candidate_import_defaults_to_all_pages_and_passes_filters(self):
        from database import list_download_candidates
        from services.supplement_candidates import generate_download_candidates_from_supplement

        info_client = AsyncMock()
        pages = {
            1: {
                "data": [{
                    "id": 11,
                    "canonical_number": "SIVR438",
                    "dvd_id": "SIVR-438",
                    "title": "First Page",
                }],
                "total_pages": 2,
            },
            2: {
                "data": [{
                    "id": 12,
                    "canonical_number": "ABP588",
                    "dvd_id": "ABP-588",
                    "title": "Second Page",
                }],
                "total_pages": 2,
            },
        }
        info_client.proxy_get.side_effect = lambda _path, params: pages[params["page"]]
        emby_client = AsyncMock()
        emby_client.check_exists.return_value = False

        result = await generate_download_candidates_from_supplement(
            info_client=info_client,
            emby_client=emby_client,
            limit=None,
            matched=False,
            missing_cover=True,
            missing_runtime=True,
            missing_maker=True,
            missing_categories=True,
            max_completeness=2,
        )

        rows = list_download_candidates(source="supplement")
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["created"], 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [call.kwargs["params"] for call in info_client.proxy_get.await_args_list],
            [
                {
                    "page": 1,
                    "page_size": 100,
                    "matched": "false",
                    "missing_cover": "true",
                    "missing_runtime": "true",
                    "missing_maker": "true",
                    "missing_categories": "true",
                    "max_completeness": 2,
                },
                {
                    "page": 2,
                    "page_size": 100,
                    "matched": "false",
                    "missing_cover": "true",
                    "missing_runtime": "true",
                    "missing_maker": "true",
                    "missing_categories": "true",
                    "max_completeness": 2,
                },
            ],
        )


class DownloadCandidateRouterTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_list_downloads_uses_short_response_cache_with_bypass(self):
        from routers import downloads

        with patch.object(downloads, "get_download_tasks", side_effect=[
            [{"id": 1, "status": "pending"}],
            [{"id": 2, "status": "downloading"}],
        ]) as tasks:
            first = await downloads.list_downloads()
            second = await downloads.list_downloads()
            bypassed = await downloads.list_downloads(cache_control="0")

        self.assertEqual(tasks.call_count, 2)
        self.assertEqual(first["data"][0]["id"], 1)
        self.assertEqual(second["data"][0]["id"], 1)
        self.assertEqual(bypassed["data"][0]["id"], 2)

    async def test_approve_candidate_requires_magnet_and_creates_download_task(self):
        from database import get_download_candidate, update_download_candidate_magnet, upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(content_id="SIVR-438", title="Title")

        with self.assertRaises(Exception):
            await downloads.approve_candidate(candidate["id"])

        update_download_candidate_magnet(candidate["id"], "magnet:?xt=urn:btih:abc")
        with patch.object(downloads.downloader_service, "create_download_task", new_callable=AsyncMock) as create_task:
            create_task.return_value = 42
            result = await downloads.approve_candidate(candidate["id"])

        self.assertEqual(result["download_task_id"], 42)
        self.assertEqual(result["candidate"]["status"], "sent")

        with self.assertRaises(Exception) as duplicate:
            await downloads.approve_candidate(candidate["id"])
        self.assertEqual(duplicate.exception.status_code, 409)

        with self.assertRaises(Exception) as reject_sent:
            await downloads.reject_candidate(candidate["id"])
        self.assertEqual(reject_sent.exception.status_code, 409)

    async def test_approve_candidate_records_failure_and_can_retry(self):
        from database import get_download_candidate, list_download_candidate_events, update_download_candidate_magnet, upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(content_id="SIVR-438", title="Title")
        update_download_candidate_magnet(candidate["id"], "magnet:?xt=urn:btih:bad")

        with patch.object(downloads.downloader_service, "create_download_task", new_callable=AsyncMock) as create_task:
            create_task.side_effect = RuntimeError("openlist timeout")
            with self.assertRaises(Exception) as failed:
                await downloads.approve_candidate(candidate["id"])

        self.assertEqual(failed.exception.status_code, 500)
        stored = get_download_candidate(candidate["id"])
        self.assertEqual(stored["status"], "failed")
        self.assertIn("openlist timeout", stored["error_msg"])
        self.assertEqual(stored["events"][0]["action"], "approve_failed")

        update_download_candidate_magnet(candidate["id"], "magnet:?xt=urn:btih:good")
        self.assertIsNone(get_download_candidate(candidate["id"])["error_msg"])

        with patch.object(downloads.downloader_service, "create_download_task", new_callable=AsyncMock) as create_task:
            create_task.return_value = 43
            result = await downloads.approve_candidate(candidate["id"])

        self.assertEqual(result["candidate"]["status"], "sent")
        self.assertEqual(result["download_task_id"], 43)
        actions = [event["action"] for event in list_download_candidate_events(candidate["id"])]
        self.assertIn("approved", actions)
        self.assertIn("approve_failed", actions)

    async def test_list_candidates_filters_status(self):
        from database import upsert_download_candidate
        from routers import downloads

        upsert_download_candidate(content_id="SIVR-438", source="subscription", status="candidate")
        upsert_download_candidate(content_id="ABP-588", source="subscription", status="candidate", magnet="magnet:?x")
        upsert_download_candidate(content_id="MIAA-999", source="inventory", status="rejected")
        upsert_download_candidate(content_id="SUPP-001", source="supplement", status="candidate")
        upsert_download_candidate(content_id="SUPP-002", source="supplement", status="sent")

        result = await downloads.list_candidates(status="candidate", needs_magnet=True, include_stats=True)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["data"][0]["content_id"], "SIVR-438")
        self.assertEqual(result["stats"]["by_source"]["subscription"], 2)
        self.assertEqual(result["stats"]["by_source"]["inventory"], 1)
        self.assertEqual(result["stats"]["by_source"]["supplement"], 2)
        self.assertEqual(result["stats"]["candidate_by_source"]["subscription"], 2)
        self.assertEqual(result["stats"]["candidate_by_source"]["supplement"], 1)

    async def test_list_candidates_paginates_with_total_pages(self):
        from database import upsert_download_candidate
        from routers import downloads

        for index in range(5):
            upsert_download_candidate(
                content_id=f"PAGE-{index}",
                source="subscription",
                status="candidate",
            )

        result = await downloads.list_candidates(status="candidate", page=2, page_size=2)

        self.assertEqual(result["total"], 5)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["page_size"], 2)
        self.assertEqual(result["total_pages"], 3)
        self.assertEqual(len(result["data"]), 2)

    async def test_list_candidates_defaults_to_page_only_without_stats_scan(self):
        from routers import downloads

        with patch.object(downloads, "list_download_candidates_page", return_value={
            "data": [{"id": 1, "content_id": "SIVR-438"}],
            "total": 1,
        }) as page_helper, \
            patch.object(downloads, "count_download_candidates", side_effect=AssertionError("extra count query")), \
            patch.object(downloads, "list_download_candidates", side_effect=AssertionError("extra list query")), \
            patch.object(downloads, "download_candidate_stats", side_effect=AssertionError("extra stats query")):
            result = await downloads.list_candidates(status="candidate", page=2, page_size=10)

        page_helper.assert_called_once_with(
            status="candidate",
            actress_id=None,
            source=None,
            q=None,
            needs_magnet=None,
            limit=10,
            offset=10,
            include_stats=False,
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["data"][0]["content_id"], "SIVR-438")
        self.assertNotIn("stats", result)

    async def test_list_candidates_can_include_stats_when_requested(self):
        from routers import downloads

        with patch.object(downloads, "list_download_candidates_page", return_value={
            "data": [{"id": 1, "content_id": "SIVR-438"}],
            "total": 1,
            "stats": {"candidate": 1},
        }) as page_helper:
            result = await downloads.list_candidates(status="candidate", page=1, page_size=10, include_stats=True)

        page_helper.assert_called_once_with(
            status="candidate",
            actress_id=None,
            source=None,
            q=None,
            needs_magnet=None,
            limit=10,
            offset=0,
            include_stats=True,
        )
        self.assertEqual(result["stats"], {"candidate": 1})

    async def test_list_candidates_uses_short_response_cache_with_bypass(self):
        from routers import downloads

        with patch.object(downloads, "list_download_candidates_page", side_effect=[
            {
                "data": [{"id": 1, "content_id": "SIVR-438"}],
                "total": 1,
            },
            {
                "data": [{"id": 2, "content_id": "ABP-588"}],
                "total": 1,
            },
        ]) as page_helper:
            first = await downloads.list_candidates(status="candidate", page=1, page_size=10)
            second = await downloads.list_candidates(status="candidate", page=1, page_size=10)
            bypassed = await downloads.list_candidates(status="candidate", page=1, page_size=10, cache_control="0")

        self.assertEqual(page_helper.call_count, 2)
        self.assertEqual(first["data"][0]["content_id"], "SIVR-438")
        self.assertEqual(second["data"][0]["content_id"], "SIVR-438")
        self.assertEqual(bypassed["data"][0]["content_id"], "ABP-588")

    async def test_candidate_summary_uses_short_response_cache_with_bypass(self):
        from routers import downloads

        with patch.object(downloads, "download_candidate_summary", side_effect=[
            {"total": 1, "candidate": 1},
            {"total": 2, "candidate": 2},
        ]) as summary:
            first = await downloads.candidate_summary(status="candidate")
            second = await downloads.candidate_summary(status="candidate")
            bypassed = await downloads.candidate_summary(status="candidate", cache_control="0")

        self.assertEqual(summary.call_count, 2)
        self.assertEqual(first["total"], 1)
        self.assertEqual(second["total"], 1)
        self.assertEqual(bypassed["total"], 2)

    async def test_candidate_summary_uses_filtered_aggregate_counts(self):
        from database import download_candidate_summary, upsert_download_candidate
        from routers import downloads

        upsert_download_candidate(
            content_id="SIVR-438",
            source="subscription",
            actress_id=101,
            status="candidate",
        )
        upsert_download_candidate(
            content_id="ABP-588",
            source="subscription",
            actress_id=101,
            status="candidate",
            magnet="magnet:?x",
        )
        upsert_download_candidate(
            content_id="MIAA-999",
            source="inventory",
            actress_id=101,
            status="candidate",
            magnet="magnet:?y",
        )
        upsert_download_candidate(
            content_id="SUPP-001",
            source="subscription",
            actress_id=202,
            status="candidate",
        )
        upsert_download_candidate(
            content_id="SUPP-002",
            source="subscription",
            actress_id=101,
            status="sent",
            magnet="magnet:?z",
        )

        db_summary = download_candidate_summary(status="candidate", actress_id=101, source="subscription")
        route_summary = await downloads.candidate_summary(status="candidate", actress_id=101, source="subscription")

        expected = {
            "total": 2,
            "candidate": 2,
            "approved": 0,
            "rejected": 0,
            "sent": 0,
            "failed": 0,
            "needs_magnet": 1,
            "ready": 1,
        }
        self.assertEqual(db_summary, expected)
        self.assertEqual(route_summary, expected)

    async def test_candidate_summary_can_include_source_counts(self):
        from database import upsert_download_candidate
        from routers import downloads

        upsert_download_candidate(content_id="SUB-001", source="subscription", status="candidate")
        upsert_download_candidate(content_id="SUB-002", source="subscription", status="sent")
        upsert_download_candidate(content_id="INV-001", source="inventory", status="candidate")
        upsert_download_candidate(content_id="SUP-001", source="supplement", status="candidate")

        result = await downloads.candidate_summary(status="candidate", include_sources=True, cache_control="0")

        self.assertEqual(result["candidate"], 3)
        self.assertEqual(result["by_source"], {
            "inventory": 1,
            "subscription": 1,
            "supplement": 1,
        })
        self.assertEqual(result["candidate_by_source"], result["by_source"])

    def test_list_download_candidates_page_skips_stats_by_default(self):
        from database import download_candidate

        with patch.object(
            download_candidate,
            "_download_candidate_stats_with_cursor",
            side_effect=AssertionError("page query should not scan global candidate stats by default"),
        ):
            result = download_candidate.list_download_candidates_page(limit=10, offset=0)

        self.assertNotIn("stats", result)

    async def test_get_candidate_returns_single_row(self):
        from database import upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(content_id="SIVR-438", source="subscription", status="candidate")
        result = downloads.get_candidate(candidate["id"])

        self.assertEqual(result["data"]["id"], candidate["id"])
        self.assertEqual(result["data"]["source"], "subscription")
        self.assertEqual(result["data"]["events"], [])

    async def test_bulk_candidate_actions_skip_sent_rows(self):
        from database import get_download_candidate, upsert_download_candidate
        from routers import downloads

        candidate = upsert_download_candidate(content_id="SIVR-438", status="candidate")
        failed = upsert_download_candidate(content_id="ABP-588", status="failed")
        sent = upsert_download_candidate(content_id="MIAA-999", status="sent")

        rejected = await downloads.bulk_reject_candidates(downloads.BulkCandidateRequest(
            ids=[candidate["id"], failed["id"], sent["id"]],
        ))
        self.assertEqual(rejected["updated"], 2)
        self.assertEqual(rejected["skipped"], 1)
        self.assertEqual(get_download_candidate(sent["id"])["status"], "sent")
        self.assertEqual(get_download_candidate(candidate["id"])["events"][0]["action"], "bulk_rejected")

        restored = await downloads.bulk_restore_candidates(downloads.BulkCandidateRequest(
            ids=[candidate["id"], failed["id"], sent["id"]],
        ))
        self.assertEqual(restored["updated"], 2)
        self.assertEqual(get_download_candidate(candidate["id"])["status"], "candidate")
        self.assertEqual(get_download_candidate(failed["id"])["status"], "candidate")


class ActorMappingRouterTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_confirm_ignore_and_list_mapping_api(self):
        from routers import inventory

        inventory.confirm_mapping(inventory.ActorMappingRequest(
            emby_actor_id="emby-1",
            emby_actor_name="Emby Name",
            javinfo_actress_id=123,
            javinfo_actress_name="Jav Name",
        ))
        inventory.ignore_mapping(inventory.ActorMappingRequest(
            emby_actor_id="emby-2",
            emby_actor_name="Ignored",
        ))

        confirmed = inventory.list_mappings(status="confirmed")
        ignored = inventory.list_mappings(status="ignored")

        self.assertEqual(len(confirmed["data"]), 1)
        self.assertEqual(confirmed["data"][0]["javinfo_actress_id"], 123)
        self.assertEqual(len(ignored["data"]), 1)


class SubscriptionRouterCandidateStatsTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_list_subscriptions_includes_candidate_counts(self):
        from database import add_subscription, upsert_download_candidate
        from routers import subscriptions

        add_subscription(123, "Actor")
        upsert_download_candidate(
            content_id="SIVR-438",
            actress_id=123,
            source="subscription",
            status="candidate",
        )

        result = await subscriptions.list_subscriptions()

        self.assertEqual(result["data"][0]["candidate_count"], 1)
        self.assertEqual(result["data"][0]["needs_magnet_count"], 1)
        self.assertEqual(result["data"][0]["mapping_status"], "javinfo")

    async def test_list_subscriptions_uses_bulk_candidate_counts(self):
        from database import add_subscription
        from routers import subscriptions

        add_subscription(123, "Actor")

        with patch.object(subscriptions, "download_candidate_counts_by_actress", return_value={
            123: {"candidate_count": 2, "needs_magnet_count": 1},
        }) as counts, \
            patch.object(subscriptions, "list_download_candidates", side_effect=AssertionError("N+1 candidate query")):
            result = await subscriptions.list_subscriptions()

        counts.assert_called_once_with(status="candidate", source="subscription")
        self.assertEqual(result["data"][0]["candidate_count"], 2)
        self.assertEqual(result["data"][0]["needs_magnet_count"], 1)

    async def test_list_subscriptions_uses_short_response_cache_with_bypass(self):
        from routers import subscriptions

        with patch.object(subscriptions, "_list_subscriptions_payload", side_effect=[
            {"data": [{"id": 1, "actress_name": "cached"}], "total": 1},
            {"data": [{"id": 2, "actress_name": "fresh"}], "total": 1},
        ]) as payload:
            first = await subscriptions.list_subscriptions()
            second = await subscriptions.list_subscriptions()
            bypassed = await subscriptions.list_subscriptions(cache_control="0")

        self.assertEqual(payload.call_count, 2)
        self.assertEqual(first["data"][0]["actress_name"], "cached")
        self.assertEqual(second["data"][0]["actress_name"], "cached")
        self.assertEqual(bypassed["data"][0]["actress_name"], "fresh")

    async def test_new_movies_groups_subscription_candidates_in_bulk(self):
        from database import add_subscription, upsert_download_candidate
        from routers import subscriptions

        add_subscription(123, "Actor")
        add_subscription(456, "Other")
        upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            title="First",
            actress_id=123,
            source="subscription",
            status="candidate",
        )
        upsert_download_candidate(
            content_id="ABP-588",
            dvd_id="ABP-588",
            title="Second",
            actress_id=456,
            source="subscription",
            status="candidate",
        )

        result = await subscriptions.get_new_movies()

        self.assertEqual(result["data"][123][0]["dvd_id"], "SIVR-438")
        self.assertEqual(result["data"][456][0]["dvd_id"], "ABP-588")

    async def test_new_movies_defaults_to_compact_candidate_batches(self):
        from routers import subscriptions

        with patch.object(subscriptions, "get_subscriptions", return_value=[
            {"id": 1, "actress_id": 123, "actress_name": "Actor", "enabled": True},
        ]), patch.object(subscriptions, "list_download_candidates_by_actress_ids", return_value={}) as rows:
            result = await subscriptions.get_new_movies()

        rows.assert_called_once_with([123], status="candidate", source="subscription", limit_per_actress=20)
        self.assertEqual(result["limit_per_actress"], 20)

    async def test_check_subscriptions_returns_structured_report(self):
        from database import add_subscription
        from routers import subscriptions

        add_subscription(123, "Actor")

        with patch("services.subscription.WatchlistPipeline") as pipeline_cls:
            pipeline = pipeline_cls.return_value
            pipeline.generate_candidates_for_actress = AsyncMock(return_value={
                "checked": 3,
                "created": 1,
                "existing": 1,
                "skipped": 0,
                "skipped_exempt": 0,
                "in_library": 1,
                "candidate_count": 2,
                "new_movies": [
                    {"candidate_id": 7, "dvd_id": "SIVR-438", "code": "SIVR-438"},
                    {"candidate_id": 8, "dvd_id": "ABP-588", "code": "ABP-588"},
                ],
            })
            result = await subscriptions.check_subscriptions()

        self.assertEqual(result["subscriptions_checked"], 1)
        self.assertEqual(result["checked"], 3)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["existing"], 1)
        self.assertEqual(result["in_library"], 1)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["new_found"], 2)
        self.assertEqual(result["results"][0]["actress_id"], 123)


class InventoryMappingGuardTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_collect_job_runs_actor_auto_match_and_records_summary(self):
        from database import add_inventory_job, get_inventory_job
        from scheduler.inventory_tasks import run_collect_job

        job_id = add_inventory_job("collect")
        fake_emby = AsyncMock()
        fake_emby.collect_all_movies_with_actors.return_value = (
            [{
                "actress_id": 901,
                "actress_name": "糸井瑠花",
                "video_count": 1,
                "items": [],
            }],
            1,
        )
        auto_match_result = {
            "snapshot_key": "snapshot",
            "checked": 1,
            "auto_confirmed": 1,
            "candidates_created": 0,
            "ambiguous": 0,
            "skipped": 0,
            "errors": [],
        }

        with (
            patch("scheduler.inventory_tasks.get_emby_client", return_value=fake_emby),
            patch("config.Config.actor_mapping_auto_match_after_collect", new_callable=PropertyMock, return_value=True),
            patch("services.actor_mapping_candidates.auto_match_actor_mappings", new=AsyncMock(return_value=auto_match_result)),
        ):
            await run_collect_job(job_id)

        job = get_inventory_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["actor_mapping"]["auto_confirmed"], 1)
        self.assertTrue(job["result"]["actor_mapping"]["enabled"])

    async def test_actor_compare_skips_unmapped_emby_actor(self):
        from database import (
            add_inventory_job,
            create_snapshot_key,
            save_emby_actors_snapshot,
            update_inventory_job,
            get_inventory_job,
        )
        from scheduler.inventory_tasks import run_actor_compare_job

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 900,
            "actress_name": "Emby Actor",
            "video_count": 1,
        }])
        job_id = add_inventory_job("actor", actor_id=900, snapshot_key=snapshot_key)

        await run_actor_compare_job(job_id, 900, snapshot_key)
        job = get_inventory_job(job_id)

        self.assertEqual(job["status"], "completed")
        self.assertIn("unmapped=1", job["error_msg"])
        self.assertEqual(job["result"]["unmapped"], 1)
        self.assertEqual(job["result"]["candidates"], 0)

    async def test_actor_compare_for_confirmed_mapping_creates_inventory_candidate(self):
        from database import (
            add_inventory_job,
            confirm_actor_mapping,
            create_snapshot_key,
            list_download_candidates,
            save_emby_actors_snapshot,
            update_inventory_actor_stats,
            get_inventory_job,
        )
        from scheduler.inventory_tasks import run_actor_compare_job

        snapshot_key = create_snapshot_key()
        save_emby_actors_snapshot(snapshot_key, [{
            "actress_id": 901,
            "actress_name": "Emby Actor",
            "video_count": 1,
        }])
        confirm_actor_mapping("901", "Emby Actor", 123, "Jav Actress")
        job_id = add_inventory_job("actor", actor_id=901, snapshot_key=snapshot_key)

        fake_pipeline = AsyncMock()
        fake_pipeline.fetch_actress_videos.return_value = [{
            "content_id": "sivr438",
            "dvd_id": "SIVR-438",
            "title_ja": "Mapped Missing",
            "release_date": "2026-05-01",
        }]
        with patch("scheduler.inventory_tasks.WatchlistPipeline", return_value=fake_pipeline):
            await run_actor_compare_job(job_id, 901, snapshot_key)

        candidates = list_download_candidates(source="inventory")
        job = get_inventory_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["dvd_id"], "SIVR-438")
        self.assertEqual(job["result"]["mapped"], 1)
        self.assertEqual(job["result"]["missing"], 1)
        self.assertEqual(job["result"]["candidates"], 1)

    async def test_full_compare_pages_snapshot_actors(self):
        from scheduler import inventory_tasks

        calls = []

        def snapshot_page(snapshot_key, page=1, page_size=50, **_kwargs):
            calls.append({"snapshot_key": snapshot_key, "page": page, "page_size": page_size})
            if page == 1:
                return {
                    "data": [
                        {"actress_id": 901, "actress_name": "Mapped"},
                        {"actress_id": 902, "actress_name": "Unmapped"},
                    ],
                    "total": 3,
                    "page": 1,
                    "page_size": page_size,
                    "total_pages": 2,
                }
            return {
                "data": [{"actress_id": 903, "actress_name": "Mapped 2"}],
                "total": 3,
                "page": 2,
                "page_size": page_size,
                "total_pages": 2,
            }

        fake_pipeline = AsyncMock()
        fake_pipeline.fetch_actress_videos.side_effect = [
            [
                {"content_id": "SIVR-438", "dvd_id": "SIVR-438", "title_ja": "Mapped 1"},
                {"content_id": "ABP-588", "dvd_id": "ABP-588", "title_ja": "Mapped 2"},
            ],
            [
                {"content_id": "MIAA-999", "dvd_id": "MIAA-999", "title_ja": "Mapped 3"},
            ],
        ]

        with patch.object(inventory_tasks, "update_inventory_job") as update_job, \
            patch.object(inventory_tasks, "update_inventory_progress"), \
            patch.object(inventory_tasks, "get_latest_snapshot_key", return_value="snap-1"), \
            patch.object(inventory_tasks, "get_snapshot_actors", side_effect=snapshot_page), \
            patch.object(inventory_tasks, "get_confirmed_actor_mapping", side_effect=lambda actor_id: (
                {"javinfo_actress_id": actor_id + 1000, "javinfo_actress_name": f"Jav {actor_id}"}
                if actor_id in {901, 903}
                else None
            )), \
            patch.object(inventory_tasks, "update_inventory_actor_stats"), \
            patch.object(inventory_tasks, "get_snapshot_videos", return_value=[
                {"filename": "SIVR-438.mp4", "title": "SIVR-438"},
                {"filename": "ABP-588.mp4", "title": "ABP-588"},
                {"filename": "MIAA-999.mp4", "title": "MIAA-999"},
            ]), \
            patch.object(inventory_tasks, "WatchlistPipeline", return_value=fake_pipeline), \
            patch.object(inventory_tasks, "add_missing_video", side_effect=AssertionError("no missing rows expected")):
            await inventory_tasks.run_compare_job(5, "snap-1")

        self.assertEqual(calls, [
            {"snapshot_key": "snap-1", "page": 1, "page_size": 100},
            {"snapshot_key": "snap-1", "page": 2, "page_size": 100},
        ])
        self.assertEqual(fake_pipeline.fetch_actress_videos.await_count, 2)
        completed = update_job.call_args_list[-1]
        self.assertEqual(completed.args[1], "completed")
        self.assertEqual(completed.kwargs["result"]["scanned"], 3)
        self.assertEqual(completed.kwargs["result"]["mapped"], 2)
        self.assertEqual(completed.kwargs["result"]["unmapped"], 1)

    async def test_inventory_actor_detail_includes_mapping_status(self):
        from database import confirm_actor_mapping, upsert_inventory_actor
        from routers import inventory

        upsert_inventory_actor(901, "Emby Actor")
        actor = await inventory.get_actor(901)
        self.assertEqual(actor["mapping_status"], "unmapped")
        self.assertIsNone(actor["actor_mapping"])

        confirm_actor_mapping("901", "Emby Actor", 123, "Jav Actress")
        actor = await inventory.get_actor(901)
        self.assertEqual(actor["mapping_status"], "confirmed")
        self.assertEqual(actor["actor_mapping"]["javinfo_actress_id"], 123)


class InventoryFillRouterTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fill_video_creates_candidate_instead_of_download_task(self):
        from database import add_missing_video, list_download_candidates, get_download_tasks
        from routers import inventory

        add_missing_video("SIVR-438", 1, "Missing", "2026-05-01", "")
        fake_info = AsyncMock()
        fake_info.get_video.return_value = {
            "content_id": "sivr438",
            "dvd_id": "SIVR-438",
            "title_ja": "Filled Candidate",
            "jacket_thumb_url": "cover.jpg",
        }
        with patch("routers.inventory.get_info_client", return_value=fake_info):
            result = await inventory.fill_video("SIVR-438")

        self.assertTrue(result["success"])
        candidates = list_download_candidates(source="inventory")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["actress_id"], 1)
        self.assertEqual(get_download_tasks(), [])
