from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from test_support.client import load_main_app_without_db


EMBY_CONFIG = {
    "emby_compat": {
        "enabled": True,
        "username": "javhub",
        "password": "secret",
    },
}

MOVIE = {
    "content_id": "ABC-123",
    "dvd_id": "ABC-123",
    "title_ja": "作品标题",
    "release_date": "2025-06-01",
    "runtime_mins": 100,
    "score": 4.2,
    "summary": "简介",
    "maker": {"id": 2, "name_ja": "片商"},
    "series": {"id": 3, "name_ja": "系列"},
    "label": {"id": 4, "name_ja": "厂牌"},
    "actresses": [
        {"id": 11, "name_kanji": "演员甲", "image_url": "https://img.example/a.jpg"}
    ],
    "categories": [{"id": 21, "name_ja": "剧情"}],
    "directors": [{"id": 31, "name_kanji": "导演甲"}],
    "actors": [{"id": 41, "name_kanji": "男演员甲"}],
    "authors": [{"id": 51, "name_kanji": "作者甲"}],
    "jacket_thumb_url": "https://pics.dmm.co.jp/mono/movie/abc123/abc123ps.jpg",
    "jacket_full_url": "https://pics.dmm.co.jp/mono/movie/abc123/abc123pl.jpg",
    "sample_image_urls": [
        "https://pics.dmm.co.jp/mono/movie/abc123/abc123jp-1.jpg",
        "https://pics.dmm.co.jp/mono/movie/abc123/abc123jp-2.jpg",
    ],
}


class EmbyCatalogStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(load_main_app_without_db())

    def setUp(self):
        self.config_patch = patch("config.config._config", EMBY_CONFIG)
        self.router_config_patch = patch("routers.emby_compat.config._config", EMBY_CONFIG)
        self.config_patch.start()
        self.router_config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.addCleanup(self.router_config_patch.stop)
        self.state_patches = [
            patch("routers.emby_compat.get_progress", return_value=None),
            patch("routers.emby_compat.get_progress_map", return_value={}),
            patch("routers.emby_compat.movie_favorite_flags", return_value={}),
            patch("routers.emby_compat.is_movie_favorite", return_value=False),
        ]
        for state_patch in self.state_patches:
            state_patch.start()
            self.addCleanup(state_patch.stop)
        login = self.client.post(
            "/Users/AuthenticateByName",
            json={"Username": "javhub", "Pw": "secret"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.auth = {"X-Emby-Token": login.json()["AccessToken"]}

    def test_generic_items_routes_browse_and_fetch_detail(self):
        info = AsyncMock()
        info.list_catalog_videos.return_value = {"data": [MOVIE], "total_count": 1}
        info.get_catalog_video.return_value = MOVIE
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.list_movie_resources",
            return_value=[],
        ):
            for path in (
                "/Items?ParentId=library&IncludeItemTypes=Movie&Recursive=true&Limit=20",
                "/items?parentid=library&includeitemtypes=Movie&recursive=true&limit=20",
            ):
                response = self.client.get(path, headers=self.auth)
                self.assertEqual(response.status_code, 200, (path, response.text))
                self.assertEqual(response.json()["Items"][0]["Id"], "ABC-123")

            detail = self.client.get("/Items/ABC-123", headers=self.auth)
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()["Name"], "作品标题")

    def test_user_items_route_accepts_lowercase_query_names(self):
        info = AsyncMock()
        info.list_catalog_videos.return_value = {"data": [MOVIE], "total_count": 1}
        with patch("modules.info_client.get_info_client", return_value=info):
            response = self.client.get(
                "/Users/javhub-emby-user/Items"
                "?parentid=library&includeitemtypes=Movie&limit=1"
                "&sortby=SortName&sortorder=Ascending",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        info.list_catalog_videos.assert_awaited_once_with(
            page=1,
            page_size=1,
            q=None,
            sort_by="title:asc",
            random_seed=None,
            include_total=True,
        )

    def test_requested_detail_fields_are_filled_from_catalog_detail(self):
        compact = {
            key: value
            for key, value in MOVIE.items()
            if key not in {
                "summary",
                "maker",
                "series",
                "label",
                "actresses",
                "categories",
                "directors",
                "actors",
                "authors",
                "sample_image_urls",
            }
        }
        info = AsyncMock()
        info.list_catalog_videos.return_value = {"data": [compact], "total_count": 1}
        info.get_catalog_video.return_value = MOVIE
        with patch("modules.info_client.get_info_client", return_value=info):
            response = self.client.get(
                "/Items?IncludeItemTypes=Movie&Limit=20"
                "&Fields=Overview,People,Genres,Studios,BackdropImageTags",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["Items"][0]
        self.assertEqual(item["Overview"], "简介")
        self.assertEqual(item["People"][0]["Name"], "演员甲")
        self.assertEqual(item["Genres"], ["剧情"])
        self.assertEqual(item["Studios"][0]["Name"], "片商")
        self.assertEqual(len(item["BackdropImageTags"]), 2)
        info.get_catalog_video.assert_awaited_once_with("ABC-123")

    def test_items_counts_uses_catalog_total_and_static_route_wins(self):
        info = AsyncMock()
        info.list_catalog_videos.return_value = {"data": [], "total_count": 1_875_511}
        with patch("modules.info_client.get_info_client", return_value=info):
            response = self.client.get("/Items/Counts", headers=self.auth)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["MovieCount"], 1_875_511)
        self.assertEqual(response.json()["SeriesCount"], 0)

    def test_persons_and_person_detail_use_javinfo_actresses(self):
        info = AsyncMock()
        info.list_actresses.return_value = {
            "data": [MOVIE["actresses"][0]],
            "total_count": 1,
        }
        info.get_actress.return_value = {
            **MOVIE["actresses"][0],
            "movie_count": 50,
        }
        with patch("modules.info_client.get_info_client", return_value=info):
            people = self.client.get("/Persons?Limit=20", headers=self.auth)
            detail = self.client.get("/Items/person:11", headers=self.auth)
        self.assertEqual(people.status_code, 200, people.text)
        self.assertEqual(people.json()["Items"][0]["Id"], "person:11")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["Type"], "Person")
        self.assertEqual(detail.json()["RecursiveItemCount"], 50)

    def test_person_filter_returns_grouped_movie_cards(self):
        info = AsyncMock()
        info.get_all_actress_videos.return_value = {
            "data": [
                MOVIE,
                {**MOVIE, "content_id": "ABC-123-DIGITAL", "service_code": "digital"},
            ],
            "total_count": 2,
        }
        collapsed = [{**MOVIE, "variant_group_count": 2}]
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.group_movie_cards",
            return_value=collapsed,
        ) as group:
            response = self.client.get(
                "/Items?PersonIds=person:11&IncludeItemTypes=Movie&Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["TotalRecordCount"], 1)
        group.assert_called_once()

    def test_latest_returns_grouped_movie_cards(self):
        page = {
            "data": [
                MOVIE,
                {**MOVIE, "content_id": "ABC-123-DIGITAL", "service_code": "digital"},
            ],
            "total_count": 2,
        }
        collapsed = [{**MOVIE, "variant_group_count": 2}]
        with patch(
            "routers.emby_compat._catalog_page",
            new=AsyncMock(return_value=page),
        ), patch(
            "routers.emby_compat.group_movie_cards",
            return_value=collapsed,
        ) as group, patch(
            "routers.emby_compat.get_progress_map",
            return_value={},
        ), patch(
            "routers.emby_compat.movie_favorite_flags",
            return_value={},
        ):
            response = self.client.get(
                "/Items/Latest?Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 1)
        group.assert_called_once()

    def test_resume_refresh_never_reads_playback_resources(self):
        info = AsyncMock()
        info.get_catalog_video.return_value = MOVIE
        progress = {
            "content_id": "ABC-123",
            "source": "library",
            "position_seconds": 120,
            "duration_seconds": 6000,
            "completed": 0,
        }
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.list_continue_watching",
            return_value=[progress],
        ), patch(
            "routers.emby_compat.movie_favorite_flags",
            return_value={},
        ), patch(
            "routers.emby_compat.list_movie_resources",
            side_effect=AssertionError("resume refresh must not enter playback domain"),
        ):
            response = self.client.get(
                "/Items/Resume?Fields=MediaSources,MediaStreams&Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("MediaSources", response.json()["Items"][0])

    def test_person_filter_combines_multiple_actor_ids(self):
        info = AsyncMock()
        info.get_all_actress_videos.side_effect = [
            {"data": [MOVIE], "total_count": 1},
            {
                "data": [{**MOVIE, "content_id": "XYZ-999", "dvd_id": "XYZ-999"}],
                "total_count": 1,
            },
        ]
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.get_progress_map",
            return_value={},
        ), patch(
            "routers.emby_compat.movie_favorite_flags",
            return_value={},
        ):
            response = self.client.get(
                "/Items?PersonIds=person:11,person:12&IncludeItemTypes=Movie&Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["TotalRecordCount"], 2)
        self.assertEqual(info.get_all_actress_videos.await_count, 2)

    def test_unknown_parent_does_not_expand_to_the_full_catalog(self):
        info = AsyncMock()
        with patch("modules.info_client.get_info_client", return_value=info):
            response = self.client.get(
                "/Items?ParentId=movie-that-is-not-a-folder&IncludeItemTypes=Movie",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["Items"], [])
        info.list_catalog_videos.assert_not_awaited()

    def test_favorite_and_played_writes_share_javhub_state(self):
        with patch("routers.emby_compat.set_movie_favorite") as set_favorite, patch(
            "routers.emby_compat.mark_movie_played"
        ) as mark_played:
            favorite = self.client.post(
                "/Users/javhub-emby-user/FavoriteItems/ABC-123",
                headers=self.auth,
            )
            played = self.client.post(
                "/Users/javhub-emby-user/PlayedItems/ABC-123",
                headers=self.auth,
            )
            unplayed = self.client.delete(
                "/Users/javhub-emby-user/PlayedItems/ABC-123",
                headers=self.auth,
            )
        self.assertEqual(favorite.status_code, 200, favorite.text)
        self.assertEqual(played.status_code, 200, played.text)
        self.assertEqual(unplayed.status_code, 200, unplayed.text)
        set_favorite.assert_called_once_with("ABC-123", True)
        self.assertEqual(mark_played.call_args_list[0].args, ("ABC-123", True))
        self.assertEqual(mark_played.call_args_list[1].args, ("ABC-123", False))

    def test_movie_dto_contains_stable_people_and_studios(self):
        from services.emby_mapper import to_base_item_dto

        dto = to_base_item_dto(
            "ABC-123",
            MOVIE,
            progress={
                "position_seconds": 600,
                "duration_seconds": 6000,
                "completed": 0,
                "updated_at": "2026-06-13T06:00:00Z",
            },
            is_favorite=True,
        )
        self.assertEqual(dto["People"][0]["Id"], "person:11")
        self.assertTrue(dto["People"][0]["PrimaryImageTag"])
        self.assertEqual(
            [(person["Name"], person["Type"]) for person in dto["People"]],
            [
                ("演员甲", "Actor"),
                ("男演员甲", "Actor"),
                ("导演甲", "Director"),
                ("作者甲", "Writer"),
            ],
        )
        self.assertEqual(dto["CommunityRating"], 8.4)
        self.assertEqual(len(dto["BackdropImageTags"]), 2)
        self.assertNotEqual(dto["BackdropImageTags"][0], dto["BackdropImageTags"][1])
        self.assertEqual(dto["Studios"][0]["Name"], "片商")
        self.assertEqual(dto["SeriesName"], "系列")
        self.assertIn("DvdId", dto["ProviderIds"])
        self.assertTrue(dto["UserData"]["IsFavorite"])
        self.assertTrue(dto["UserData"]["IsResumable"])
        self.assertEqual(dto["UserData"]["LastPlayedDate"], "2026-06-13T06:00:00Z")

    def test_list_items_batches_progress_and_favorite_state(self):
        info = AsyncMock()
        info.list_catalog_videos.return_value = {"data": [MOVIE], "total_count": 1}
        progress = {
            "ABC-123": {
                "content_id": "ABC-123",
                "position_seconds": 120,
                "duration_seconds": 6000,
                "completed": 0,
            }
        }
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.get_progress_map",
            return_value=progress,
        ) as progress_map, patch(
            "routers.emby_compat.movie_favorite_flags",
            return_value={"ABC-123": True},
        ) as favorite_flags:
            response = self.client.get(
                "/Items?IncludeItemTypes=Movie&Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        user_data = response.json()["Items"][0]["UserData"]
        self.assertTrue(user_data["IsFavorite"])
        self.assertTrue(user_data["IsResumable"])
        progress_map.assert_called_once_with(["ABC-123"], source="library")
        favorite_flags.assert_called_once_with(["ABC-123"])

    def test_favorite_filter_uses_state_ids_before_metadata_fetch(self):
        info = AsyncMock()
        info.get_catalog_video.return_value = MOVIE
        with patch("modules.info_client.get_info_client", return_value=info), patch(
            "routers.emby_compat.select_state_movie_ids",
            return_value=["ABC-123"],
        ), patch(
            "routers.emby_compat.get_progress_map",
            return_value={},
        ), patch(
            "routers.emby_compat.movie_favorite_flags",
            return_value={"ABC-123": True},
        ):
            response = self.client.get(
                "/Items?Filters=IsFavorite&SortBy=DatePlayed&Limit=20",
                headers=self.auth,
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["TotalRecordCount"], 1)
        self.assertTrue(response.json()["Items"][0]["UserData"]["IsFavorite"])
        info.list_catalog_videos.assert_not_awaited()

    def test_empty_collection_routes_return_protocol_envelope(self):
        for path in ("/Genres", "/Shows/Upcoming", "/Artists"):
            response = self.client.get(path, headers=self.auth)
            self.assertEqual(response.status_code, 200, (path, response.text))
            self.assertEqual(response.json()["Items"], [])


if __name__ == "__main__":
    unittest.main()
