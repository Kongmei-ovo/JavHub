from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, Mock, patch

from test_support.cache import FakeRedisMixin


class InventoryOverviewRouteTest(FakeRedisMixin, unittest.IsolatedAsyncioTestCase):
    def test_db_bound_inventory_get_handlers_are_sync_for_threadpool_dispatch(self):
        from routers import inventory

        handlers = [
            inventory.get_latest_snapshot,
            inventory.list_jobs,
            inventory.get_job,
            inventory.list_mappings,
            inventory.actor_mapping_summary,
            inventory.list_unmapped_actor_mappings,
            inventory.find_similar_actors,
            inventory.list_missing,
            inventory.list_missing_by_actor,
            inventory.list_exempt,
            inventory.list_aliases,
        ]

        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                self.assertFalse(inspect.iscoroutinefunction(handler))

    def test_cached_inventory_actor_route_is_async_to_avoid_threadpool_queueing(self):
        from routers import inventory

        self.assertTrue(inspect.iscoroutinefunction(inventory.list_actors))

    def test_latest_snapshot_defaults_to_lightweight_metadata(self):
        from routers import inventory

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")) as latest, \
            patch.object(inventory, "count_snapshot_actors", Mock(return_value=123)) as actor_count, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("default snapshot metadata should not fetch actor rows"))):
            result = inventory.get_latest_snapshot()

        latest.assert_called_once()
        actor_count.assert_called_once_with("snap-1")
        self.assertEqual(result["snapshot_key"], "snap-1")
        self.assertEqual(result["actor_count"], 123)
        self.assertEqual(result["actors"], {"data": [], "total": 123, "deferred": True})

    def test_latest_snapshot_can_include_actor_page_when_requested(self):
        from routers import inventory

        actor_page = {"data": [{"actress_id": 1}], "total": 1, "page": 1, "page_size": 50, "total_pages": 1}
        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(inventory, "count_snapshot_actors", Mock(return_value=1)), \
            patch.object(inventory, "get_snapshot_actors", Mock(return_value=actor_page)) as snapshot_actors:
            result = inventory.get_latest_snapshot(include_actors=True)

        snapshot_actors.assert_called_once_with("snap-1")
        self.assertEqual(result["actors"], actor_page)

    def test_inventory_actors_payload_bulk_resolves_alias_display_names(self):
        from routers import inventory

        with patch.object(inventory, "get_snapshot_actors_with_inventory_stats", Mock(return_value={
                "data": [
                    {"actress_id": 10, "actress_name": "Alias A", "total_videos": 5, "image_tag": ""},
                    {"actress_id": 20, "actress_name": "Primary B", "total_videos": 3, "image_tag": ""},
                ],
                "total": 2,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
            })) as snapshot_actors, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("missing_count sort should use joined snapshot stats"))), \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[
                {"actress_id": 10, "missing_count": 4, "primary_name": ""},
                {"actress_id": 20, "missing_count": 1, "primary_name": "Canonical B"},
            ])) as inventory_actors, \
            patch.object(inventory, "get_inventory_actors", Mock(side_effect=AssertionError("should not fetch every inventory actor"))), \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[
                {"alias_id": 10, "canonical_id": 20},
            ])) as aliases, \
            patch.object(inventory, "get_canonical_actress_id", Mock(side_effect=AssertionError("per-row alias lookup"))), \
            patch.object(inventory, "get_actor_primary_name", Mock(side_effect=AssertionError("per-row primary lookup"))):
            result = inventory._inventory_actors_payload("snap-1")

        snapshot_actors.assert_called_once()
        inventory_actors.assert_called_once_with([10, 20])
        aliases.assert_called_once()
        self.assertEqual([actor["display_name"] for actor in result["data"]], ["Canonical B", "Canonical B"])
        self.assertEqual([actor["missing_count"] for actor in result["data"]], [4, 1])

    def test_inventory_actors_payload_fetches_inventory_rows_for_current_page_only(self):
        from routers import inventory

        with patch.object(inventory, "get_snapshot_actors_with_inventory_stats", Mock(return_value={
                "data": [
                    {"actress_id": 10, "actress_name": "Alias A", "total_videos": 5, "image_tag": ""},
                    {"actress_id": 20, "actress_name": "Primary B", "total_videos": 3, "image_tag": ""},
                ],
                "total": 2,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
            })), \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("missing_count sort should use joined snapshot stats"))), \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[
                {"actress_id": 10, "missing_count": 4, "primary_name": ""},
                {"actress_id": 20, "missing_count": 1, "primary_name": "Canonical B"},
            ])) as inventory_actors, \
            patch.object(inventory, "get_inventory_actors", Mock(side_effect=AssertionError("should not fetch every inventory actor"))), \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[
                {"alias_id": 10, "canonical_id": 20},
            ])):
            result = inventory._inventory_actors_payload("snap-1")

        inventory_actors.assert_called_once_with([10, 20])
        self.assertEqual([actor["display_name"] for actor in result["data"]], ["Canonical B", "Canonical B"])
        self.assertEqual([actor["missing_count"] for actor in result["data"]], [4, 1])

    def test_inventory_actors_payload_sorts_missing_count_in_database_before_paging(self):
        from routers import inventory

        with patch.object(inventory, "get_snapshot_actors_with_inventory_stats", Mock(return_value={
                "data": [
                    {"actress_id": 30, "actress_name": "High", "total_videos": 9, "image_tag": "", "missing_count": 8},
                    {"actress_id": 20, "actress_name": "Mid", "total_videos": 7, "image_tag": "", "missing_count": 5},
                ],
                "total": 5,
                "page": 2,
                "page_size": 2,
                "total_pages": 3,
            }), create=True) as snapshot_with_stats, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("missing_count sort should happen before paging"))), \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[
                {"actress_id": 20, "missing_count": 5, "primary_name": ""},
                {"actress_id": 30, "missing_count": 8, "primary_name": ""},
            ])), \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[])):
            result = inventory._inventory_actors_payload(
                "snap-1",
                search="ai",
                actor_sort="missing_count",
                page=2,
                page_size=2,
            )

        snapshot_with_stats.assert_called_once_with(
            "snap-1",
            search="ai",
            sort_order="desc",
            page=2,
            page_size=2,
        )
        self.assertEqual([actor["actress_id"] for actor in result["data"]], [30, 20])
        self.assertEqual(result["total_pages"], 3)

    def test_unmapped_actor_payload_reuses_mapping_snapshot(self):
        from routers import inventory

        with patch.object(inventory, "get_snapshot_actors", Mock(return_value={
                "data": [
                    {"actress_id": 10, "actress_name": "A", "total_videos": 5, "image_tag": ""},
                    {"actress_id": 20, "actress_name": "B", "total_videos": 1, "image_tag": ""},
                ],
            })), \
            patch("services.actor_mapping_candidates.mapping_candidate_from_row", side_effect=lambda row: {
                "id": row["javinfo_actress_id"],
                "name": row["javinfo_actress_name"],
            }), \
            patch.object(inventory, "list_actor_mappings_for_actor_ids", Mock(return_value=[
                {
                    "emby_actor_id": "10",
                    "emby_actor_name": "A",
                    "javinfo_actress_id": 100,
                    "javinfo_actress_name": "A Prime",
                    "status": "candidate",
                },
                {
                    "emby_actor_id": "20",
                    "emby_actor_name": "B",
                    "javinfo_actress_id": None,
                    "javinfo_actress_name": "",
                    "status": "ignored",
                },
            ])) as mappings:
            result = inventory._unmapped_actor_mappings_payload(snapshot_key="snap-1")

        mappings.assert_called_once_with(["10", "20"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["data"][0]["emby_actor_id"], "10")
        self.assertEqual(result["data"][0]["candidate_count"], 1)

    def test_unmapped_actor_payload_pages_snapshot_until_limit(self):
        from routers import inventory

        calls = []

        def snapshot_page(snapshot_key, search=None, page=1, page_size=50, **_kwargs):
            calls.append({"snapshot_key": snapshot_key, "search": search, "page": page, "page_size": page_size})
            if page == 1:
                return {
                    "data": [
                        {"actress_id": 10, "actress_name": "Mapped", "total_videos": 3, "image_tag": ""},
                        {"actress_id": 20, "actress_name": "Open", "total_videos": 2, "image_tag": ""},
                    ],
                    "total": 3,
                    "page": 1,
                    "page_size": page_size,
                    "total_pages": 2,
                }
            return {
                "data": [{"actress_id": 30, "actress_name": "Next", "total_videos": 1, "image_tag": ""}],
                "total": 3,
                "page": 2,
                "page_size": page_size,
                "total_pages": 2,
            }

        with patch.object(inventory, "get_snapshot_actors", Mock(side_effect=snapshot_page)), \
            patch("services.actor_mapping_candidates.mapping_candidate_from_row", side_effect=lambda row: {"id": row["javinfo_actress_id"]}), \
            patch.object(inventory, "list_actor_mappings_for_actor_ids", Mock(side_effect=[
                [
                    {"emby_actor_id": "10", "javinfo_actress_id": 100, "status": "confirmed"},
                    {"emby_actor_id": "20", "javinfo_actress_id": 200, "status": "candidate"},
                ],
                [],
            ])) as mappings:
            result = inventory._unmapped_actor_mappings_payload(search="a", limit=2, snapshot_key="snap-1")

        self.assertEqual(mappings.call_args_list[0].args[0], ["10", "20"])
        self.assertEqual(mappings.call_args_list[1].args[0], ["30"])
        self.assertEqual(calls, [
            {"snapshot_key": "snap-1", "search": "a", "page": 1, "page_size": 80},
            {"snapshot_key": "snap-1", "search": "a", "page": 2, "page_size": 80},
        ])
        self.assertEqual(result["total"], 2)
        self.assertEqual([row["emby_actor_id"] for row in result["data"]], ["20", "30"])

    def test_unmapped_actor_payload_fetches_mapping_rows_for_current_page_only(self):
        from routers import inventory

        with patch.object(inventory, "get_snapshot_actors", Mock(return_value={
                "data": [
                    {"actress_id": 10, "actress_name": "Mapped", "total_videos": 3, "image_tag": ""},
                    {"actress_id": 20, "actress_name": "Open", "total_videos": 2, "image_tag": ""},
                ],
                "total": 2,
                "page": 1,
                "page_size": 80,
                "total_pages": 1,
            })) as snapshot_actors, \
            patch.object(inventory, "list_actor_mappings_for_actor_ids", Mock(return_value=[
                {"emby_actor_id": "10", "javinfo_actress_id": 100, "status": "confirmed"},
                {"emby_actor_id": "20", "javinfo_actress_id": 200, "status": "candidate"},
            ])) as mappings, \
            patch("services.actor_mapping_candidates.mapping_candidate_from_row", side_effect=lambda row: {
                "id": row["javinfo_actress_id"],
            }), \
            patch("database.list_actor_mappings", Mock(side_effect=AssertionError("should not fetch global mappings")), create=True):
            result = inventory._unmapped_actor_mappings_payload(limit=80, snapshot_key="snap-1")

        snapshot_actors.assert_called_once_with("snap-1", search=None, page=1, page_size=80)
        mappings.assert_called_once_with(["10", "20"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["data"][0]["emby_actor_id"], "20")
        self.assertEqual(result["data"][0]["candidate_count"], 1)

    async def test_list_actors_preserves_requested_sort_field_and_direction(self):
        from routers import inventory

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(inventory, "get_snapshot_actors", Mock(return_value={
                "data": [],
                "total": 0,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
            })) as snapshot_actors, \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[])), \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[])):
            result = await inventory.list_actors(sort_by="total_videos", sort_order="asc", cache_control="0")

        self.assertEqual(result["data"], [])
        self.assertEqual(snapshot_actors.call_args.kwargs["sort_by"], "total_videos")
        self.assertEqual(snapshot_actors.call_args.kwargs["sort_order"], "asc")

    async def test_list_actors_sorts_missing_count_in_requested_direction(self):
        from routers import inventory

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(inventory, "get_snapshot_actors_with_inventory_stats", Mock(return_value={
                "data": [
                    {"actress_id": 2, "actress_name": "B", "total_videos": 5, "image_tag": "", "missing_count": 1},
                    {"actress_id": 1, "actress_name": "A", "total_videos": 5, "image_tag": "", "missing_count": 5},
                ],
                "total": 2,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
            })) as snapshot_actors, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("missing_count sort should use joined snapshot stats"))), \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[
                {"actress_id": 1, "missing_count": 5},
                {"actress_id": 2, "missing_count": 1},
            ])), \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[])):
            result = await inventory.list_actors(sort_by="missing_count", sort_order="asc", cache_control="0")

        self.assertEqual(snapshot_actors.call_args.kwargs["sort_order"], "asc")
        self.assertEqual([actor["actress_id"] for actor in result["data"]], [2, 1])

    async def test_list_actors_uses_short_response_cache_with_bypass(self):
        from routers import inventory

        with patch.object(inventory, "_inventory_actors_payload", side_effect=[
            {"data": [{"actress_id": 1}], "total": 1, "page": 1, "page_size": 20, "total_pages": 1},
            {"data": [{"actress_id": 2}], "total": 1, "page": 1, "page_size": 20, "total_pages": 1},
        ]) as payload, \
            patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")):
            first = await inventory.list_actors(page=1, page_size=20)
            second = await inventory.list_actors(page=1, page_size=20)
            bypassed = await inventory.list_actors(page=1, page_size=20, cache_control="0")

        self.assertEqual(payload.call_count, 2)
        self.assertEqual(first["data"][0]["actress_id"], 1)
        self.assertEqual(second["data"][0]["actress_id"], 1)
        self.assertEqual(bypassed["data"][0]["actress_id"], 2)

    async def test_overview_returns_first_screen_inventory_payload(self):
        from routers import inventory

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")) as latest, \
            patch.object(inventory, "count_snapshot_actors", Mock(return_value=1)) as actor_count, \
            patch.object(inventory, "get_snapshot_actors_with_inventory_stats", Mock(return_value={
                "data": [{"actress_id": 1, "actress_name": "A", "total_videos": 5, "image_tag": "tag"}],
                "total": 1,
                "page": 1,
                "page_size": 60,
                "total_pages": 1,
            })) as snapshot_actors, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("missing_count sort should use joined snapshot stats"))), \
            patch.object(inventory, "get_inventory_actors_by_ids", Mock(return_value=[
                {"actress_id": 1, "missing_count": 2, "primary_name": "Primary A"},
            ])) as inventory_actors, \
            patch.object(inventory, "get_actor_aliases", Mock(return_value=[])), \
            patch.object(inventory, "mapping_summary_for_snapshot", Mock(return_value={
                "total": 1,
                "confirmed": 0,
                "ignored": 0,
                "candidate": 1,
                "unmapped": 1,
                "coverage": 0,
            }), create=True) as mapping, \
            patch.object(inventory, "_unmapped_actor_mappings_payload", Mock(return_value={
                "data": [{"emby_actor_id": "1", "emby_actor_name": "A"}],
                "total": 1,
                "snapshot_key": "snap-1",
            })) as unmapped, \
            patch.object(inventory, "list_missing_videos_page", Mock(return_value={
                "data": [{"content_id": "SIVR-438", "actress_id": 1, "actress_name": "A"}],
                "total": 120,
            }), create=True) as missing, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("overview should page missing videos"))), \
            patch.object(inventory, "list_download_candidates_page", Mock(return_value={
                "data": [{"id": 10, "status": "candidate", "source": "inventory"}],
                "total": 1,
            }), create=True) as candidates, \
            patch.object(inventory, "download_candidate_summary", Mock(return_value={
                "candidate": 1,
                "needs_magnet": 1,
            }), create=True) as candidate_summary, \
            patch.object(inventory, "list_download_candidates", Mock(side_effect=AssertionError("extra list query")), create=True), \
            patch.object(inventory, "count_download_candidates", Mock(side_effect=AssertionError("extra count query")), create=True), \
            patch.object(inventory, "download_candidate_stats", Mock(side_effect=AssertionError("extra stats query")), create=True), \
            patch.object(inventory, "_snapshot_duplicates", Mock(side_effect=AssertionError("overview should defer duplicate scan"))), \
            patch.object(inventory, "get_inventory_jobs", Mock(return_value=[
                {"id": 5, "status": "running"},
            ])) as jobs:
            result = await inventory.library_organize_overview(candidate_status=None)

        latest.assert_called_once()
        actor_count.assert_called_once_with("snap-1")
        self.assertEqual(snapshot_actors.call_args.kwargs, {
            "search": None,
            "sort_order": "desc",
            "page": 1,
            "page_size": 60,
        })
        inventory_actors.assert_called_once_with([1])
        mapping.assert_called_once_with("snap-1")
        unmapped.assert_called_once_with(search=None, limit=80, snapshot_key="snap-1")
        missing.assert_called_once_with(limit=80, offset=0)
        candidates.assert_called_once_with(
            status=None,
            actress_id=None,
            source="inventory",
            q=None,
            needs_magnet=None,
            limit=80,
            offset=0,
            include_stats=False,
        )
        candidate_summary.assert_called_once_with(status="candidate", source="inventory")
        jobs.assert_called_once_with(limit=50)
        self.assertEqual(result["snapshot"]["snapshot_key"], "snap-1")
        self.assertEqual(result["actors"]["data"][0]["display_name"], "Primary A")
        self.assertEqual(result["mapping"]["summary"]["candidate"], 1)
        self.assertEqual(result["missing"]["total"], 120)
        self.assertEqual(len(result["missing"]["data"]), 1)
        self.assertEqual(result["candidates"]["total"], 1)
        self.assertEqual(result["candidates"]["stats"]["candidate"], 1)
        self.assertEqual(result["duplicates"], {"data": [], "total": 0, "deferred": True})
        self.assertEqual(result["jobs"]["data"][0]["status"], "running")

    def test_actor_mapping_summary_uses_db_summary_without_full_snapshot_rows(self):
        from routers import inventory

        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")) as latest, \
            patch.object(inventory, "mapping_summary_for_snapshot", Mock(return_value={
                "total": 10,
                "confirmed": 3,
                "ignored": 2,
                "candidate": 4,
                "unmapped": 5,
                "coverage": 0.3,
            })) as summary, \
            patch.object(inventory, "get_snapshot_actors", Mock(side_effect=AssertionError("summary should not fetch full snapshot rows"))):
            result = inventory.actor_mapping_summary()

        latest.assert_called_once()
        summary.assert_called_once_with("snap-1")
        self.assertEqual(result["snapshot_key"], "snap-1")
        self.assertEqual(result["confirmed"], 3)

    def test_find_similar_actors_passes_bounded_limits_to_database_search(self):
        from routers import inventory

        similar = [{
            "actor_a": {"actress_id": 1, "actress_name": "A", "image_tag": ""},
            "actor_b": {"actress_id": 2, "actress_name": "B", "image_tag": ""},
            "similarity": 0.9,
        }]
        with patch.object(inventory, "get_latest_snapshot_key", Mock(return_value="snap-1")), \
            patch.object(inventory, "find_similar_actresses", Mock(return_value=similar)) as finder:
            result = inventory.find_similar_actors(name="ai", threshold=0.7, limit=9999, candidate_limit=9999)

        finder.assert_called_once_with("snap-1", "ai", 0.7, limit=200, candidate_limit=1000)
        self.assertEqual(result["data"], similar)
        self.assertEqual(result["limit"], 200)
        self.assertEqual(result["candidate_limit"], 1000)

    def test_find_similar_actresses_uses_bounded_snapshot_page(self):
        from database import snapshot

        calls = []

        def snapshot_page(snapshot_key, search=None, sort_by=None, sort_order="asc", page=1, page_size=50):
            calls.append({
                "snapshot_key": snapshot_key,
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": page,
                "page_size": page_size,
            })
            return {
                "data": [
                    {"actress_id": 1, "actress_name": "Aika"},
                    {"actress_id": 2, "actress_name": "Aika Prime"},
                    {"actress_id": 3, "actress_name": "Unrelated"},
                ],
            }

        with patch.object(snapshot, "get_snapshot_actors", Mock(side_effect=snapshot_page)):
            result = snapshot.find_similar_actresses(
                "snap-1",
                name="Ai",
                threshold=0.1,
                limit=1,
                candidate_limit=2,
            )

        self.assertEqual(calls, [{
            "snapshot_key": "snap-1",
            "search": "Ai",
            "sort_by": "total_videos",
            "sort_order": "desc",
            "page": 1,
            "page_size": 2,
        }])
        self.assertEqual(len(result), 1)
        self.assertGreaterEqual(result[0]["similarity"], 0.1)

    async def test_auto_match_route_clamps_large_frontend_limit(self):
        from routers import inventory

        with patch("services.actor_mapping_candidates.auto_match_actor_mappings", new=AsyncMock(return_value={
            "checked": 500,
            "auto_confirmed": 1,
        })) as auto_match:
            result = await inventory.auto_match_mappings(limit=100000, dry_run=True)

        auto_match.assert_awaited_once_with(search=None, limit=2000, dry_run=True)
        self.assertEqual(result["limit"], 2000)

    def test_list_missing_defaults_to_first_page(self):
        from routers import inventory

        with patch.object(inventory, "list_missing_videos_page", Mock(return_value={
            "data": [{"content_id": "A"}],
            "total": 300,
            "limit": 80,
            "offset": 0,
        })) as page, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("missing route should be paged"))):
            result = inventory.list_missing()

        page.assert_called_once_with(limit=80, offset=0)
        self.assertEqual(result, {
            "data": [{"content_id": "A"}],
            "total": 300,
            "page": 1,
            "page_size": 80,
            "total_pages": 4,
        })

    async def test_fill_video_uses_indexed_missing_lookup(self):
        from routers import inventory

        info_client = Mock()
        info_client.get_video = AsyncMock(return_value={
            "content_id": "SIVR-438",
            "dvd_id": "SIVR-438",
            "title_ja": "Title",
            "jacket_thumb_url": "thumb",
            "release_date": "2026-01-01",
        })

        with patch.object(inventory, "get_missing_video", Mock(return_value={
                "content_id": "SIVR-438",
                "actress_id": 7,
                "title": "Fallback",
                "jacket_thumb_url": "old-thumb",
                "release_date": "2025-01-01",
            })) as missing_lookup, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("single fill should not scan all missing videos"))), \
            patch.object(inventory, "get_info_client", Mock(return_value=info_client)), \
            patch("database.upsert_download_candidate", Mock(return_value={"id": 10}), create=True) as upsert:
            result = await inventory.fill_video("SIVR-438")

        missing_lookup.assert_called_once_with("SIVR-438")
        upsert.assert_called_once()
        self.assertEqual(upsert.call_args.kwargs["actress_id"], 7)
        self.assertEqual(result["candidate"], {"id": 10})

    async def test_fill_all_pages_missing_videos_and_returns_bounded_candidate_sample(self):
        from routers import inventory

        info_client = Mock()
        info_client.get_video = AsyncMock(side_effect=[
            {"content_id": "A-001", "dvd_id": "A-001", "title_ja": "A"},
            {"content_id": "A-002", "dvd_id": "A-002", "title_ja": "B"},
            {"content_id": "A-003", "dvd_id": "A-003", "title_ja": "C"},
        ])

        with patch.object(inventory, "list_missing_videos_page", Mock(return_value={
                "data": [
                    {"content_id": "A-001", "actress_id": 1, "title": "A"},
                    {"content_id": "A-002", "actress_id": 1, "title": "B"},
                    {"content_id": "A-003", "actress_id": 1, "title": "C"},
                ],
                "total": 8,
                "limit": 3,
                "offset": 0,
            })) as page, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("fill-all should page missing videos"))), \
            patch.object(inventory, "get_info_client", Mock(return_value=info_client)), \
            patch("database.upsert_download_candidate", Mock(side_effect=[
                {"id": 1, "content_id": "A-001"},
                {"id": 2, "content_id": "A-002"},
                {"id": 3, "content_id": "A-003"},
            ]), create=True) as upsert:
            result = await inventory.fill_all_videos(limit=3, sample_limit=2)

        page.assert_called_once_with(limit=3, offset=0)
        self.assertEqual(upsert.call_count, 3)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["total"], 8)
        self.assertEqual(result["limit"], 3)
        self.assertEqual(result["offset"], 0)
        self.assertEqual(result["has_more"], True)
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["truncated"], True)
        self.assertEqual(result["candidates"], [
            {"id": 1, "content_id": "A-001"},
            {"id": 2, "content_id": "A-002"},
        ])

    async def test_fill_all_clamps_requested_limit(self):
        from routers import inventory

        info_client = Mock()
        info_client.get_video = AsyncMock(return_value={
            "content_id": "A-001",
            "dvd_id": "A-001",
            "title_ja": "A",
        })

        with patch.object(inventory, "list_missing_videos_page", Mock(return_value={
                "data": [
                    {"content_id": "A-001", "actress_id": 1, "title": "A"},
                ],
                "total": 1,
                "limit": 100,
                "offset": 0,
            })) as page, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("fill-all should page missing videos"))), \
            patch.object(inventory, "get_info_client", Mock(return_value=info_client)), \
            patch("database.upsert_download_candidate", Mock(return_value={"id": 1, "content_id": "A-001"}), create=True):
            result = await inventory.fill_all_videos(limit=10000, sample_limit=10)

        page.assert_called_once_with(limit=100, offset=0)
        self.assertEqual(result["limit"], 100)
        self.assertEqual(result["offset"], 0)
        self.assertEqual(result["has_more"], False)

    async def test_fill_all_can_resume_from_offset(self):
        from routers import inventory

        info_client = Mock()
        info_client.get_video = AsyncMock(side_effect=[
            {"content_id": "A-004", "dvd_id": "A-004", "title_ja": "D"},
            {"content_id": "A-005", "dvd_id": "A-005", "title_ja": "E"},
        ])

        with patch.object(inventory, "list_missing_videos_page", Mock(return_value={
                "data": [
                    {"content_id": "A-004", "actress_id": 1, "title": "D"},
                    {"content_id": "A-005", "actress_id": 1, "title": "E"},
                ],
                "total": 5,
                "limit": 2,
                "offset": 3,
            })) as page, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("fill-all should page missing videos"))), \
            patch.object(inventory, "get_info_client", Mock(return_value=info_client)), \
            patch("database.upsert_download_candidate", Mock(side_effect=[
                {"id": 4, "content_id": "A-004"},
                {"id": 5, "content_id": "A-005"},
            ]), create=True):
            result = await inventory.fill_all_videos(limit=2, offset=3, sample_limit=5)

        page.assert_called_once_with(limit=2, offset=3)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["offset"], 3)
        self.assertEqual(result["has_more"], False)

    async def test_fill_all_legacy_sample_limit_defaults_to_first_page(self):
        from routers import inventory

        info_client = Mock()
        info_client.get_video = AsyncMock(side_effect=[
            {"content_id": "A-001", "dvd_id": "A-001", "title_ja": "A"},
            {"content_id": "A-002", "dvd_id": "A-002", "title_ja": "B"},
            {"content_id": "A-003", "dvd_id": "A-003", "title_ja": "C"},
        ])

        with patch.object(inventory, "list_missing_videos_page", Mock(return_value={
                "data": [
                    {"content_id": "A-001", "actress_id": 1, "title": "A"},
                    {"content_id": "A-002", "actress_id": 1, "title": "B"},
                    {"content_id": "A-003", "actress_id": 1, "title": "C"},
                ],
                "total": 3,
                "limit": 100,
                "offset": 0,
            })) as page, \
            patch.object(inventory, "get_all_missing_videos", Mock(side_effect=AssertionError("fill-all should page missing videos"))), \
            patch.object(inventory, "get_info_client", Mock(return_value=info_client)), \
            patch("database.upsert_download_candidate", Mock(side_effect=[
                {"id": 1, "content_id": "A-001"},
                {"id": 2, "content_id": "A-002"},
                {"id": 3, "content_id": "A-003"},
            ]), create=True) as upsert:
            result = await inventory.fill_all_videos(sample_limit=2)

        page.assert_called_once_with(limit=100, offset=0)
        self.assertEqual(upsert.call_count, 3)
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["truncated"], True)

if __name__ == "__main__":
    unittest.main()
