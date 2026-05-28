from __future__ import annotations
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class SupplementConfigTest(unittest.TestCase):
    def test_supplement_admin_token_reads_env_var(self):
        from config import Config
        with patch.dict('os.environ', {'SUPPLEMENT_ADMIN_TOKEN': 'test-secret'}, clear=False):
            cfg = Config.__new__(Config)
            cfg._config = {}
            self.assertEqual(cfg.supplement_admin_token, 'test-secret')

    def test_supplement_admin_token_falls_back_to_config(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {'javinfo': {'supplement_admin_token': 'yaml-token'}}
        with patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
            self.assertEqual(cfg.supplement_admin_token, 'yaml-token')

    def test_supplement_admin_token_defaults_empty(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {}
        import os
        os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
        self.assertEqual(cfg.supplement_admin_token, '')

    def test_update_deep_merges_nested_config_without_clearing_secrets(self):
        from config import Config
        from routers.config import _strip_blank_sensitive_values
        cfg = Config.__new__(Config)
        cfg._config = {
            'emby': {'api_url': 'http://emby', 'api_key': 'secret-key'},
            'openlist': {'username': 'user', 'password': 'secret-password', 'default_path': '/old'},
            'javinfo': {'api_url': 'http://old:8080', 'page_size': 30, 'supplement_admin_token': 'admin-token'},
        }

        with patch('config.Path') as path_mock, patch('config.yaml.dump') as dump_mock:
            fake_path = MagicMock()
            fake_path.__truediv__.return_value = fake_path
            fake_path.parent.parent = fake_path
            fake_path.exists.return_value = True
            fake_path.open = MagicMock()
            path_mock.return_value = fake_path
            with patch('builtins.open', MagicMock()):
                cfg.update(_strip_blank_sensitive_values({
                    'emby': {'api_url': 'http://new-emby'},
                    'openlist': {'password': '', 'default_path': '/new'},
                    'javinfo': {'page_size': 50, 'supplement_admin_token': ''},
                }))

        self.assertEqual(cfg._config['emby']['api_key'], 'secret-key')
        self.assertEqual(cfg._config['emby']['api_url'], 'http://new-emby')
        self.assertEqual(cfg._config['openlist']['password'], 'secret-password')
        self.assertEqual(cfg._config['openlist']['default_path'], '/new')
        self.assertEqual(cfg._config['javinfo']['supplement_admin_token'], 'admin-token')
        self.assertEqual(cfg._config['javinfo']['page_size'], 50)
        dump_mock.assert_called_once()

    def test_blank_sensitive_values_are_ignored_but_new_values_are_kept(self):
        from routers.config import _strip_blank_sensitive_values
        payload = _strip_blank_sensitive_values({
            'emby': {'api_key': '', 'api_url': 'http://emby'},
            'telegram': {'bot_token': 'new-token'},
            'openlist': {'password': None, 'username': 'user'},
        })
        self.assertNotIn('api_key', payload['emby'])
        self.assertNotIn('password', payload['openlist'])
        self.assertEqual(payload['telegram']['bot_token'], 'new-token')

    def test_config_sanitization_treats_suffixed_secrets_as_sensitive(self):
        from routers.config import _sanitize_config
        payload = _sanitize_config({
            'javinfo': {'api_url': 'http://old:8080', 'supplement_admin_token': 'admin-token'},
            'nested': {'custom_secret': 'hidden', 'visible': 'ok'},
        })
        self.assertNotIn('supplement_admin_token', payload['javinfo'])
        self.assertNotIn('custom_secret', payload['nested'])
        self.assertEqual(payload['nested']['visible'], 'ok')

    def test_get_all_exposes_runtime_javinfo_url_with_env_override(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {'javinfo': {'api_url': 'http://localhost:8080', 'page_size': 30}}
        with patch.dict('os.environ', {'JAVINFO_API_URL': 'http://javinfo.internal:18080'}, clear=False):
            self.assertEqual(cfg.get_all()['javinfo']['api_url'], 'http://javinfo.internal:18080')

    def test_docker_env_overrides_yaml_localhost_javinfo_url(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {'javinfo': {'api_url': 'http://localhost:18080', 'page_size': 30}}
        with patch.dict('os.environ', {'JAVINFO_API_URL': 'http://javinfoapi:18080'}, clear=False):
            self.assertEqual(cfg.javinfo_api_url, 'http://javinfoapi:18080')
            self.assertEqual(cfg.get_all()['javinfo']['api_url'], 'http://javinfoapi:18080')

    def test_local_javinfo_url_still_comes_from_yaml_without_env_override(self):
        from config import Config
        cfg = Config.__new__(Config)
        cfg._config = {'javinfo': {'api_url': 'http://127.0.0.1:8080', 'page_size': 30}}
        with patch.dict('os.environ', {}, clear=False):
            os.environ.pop('JAVINFO_API_URL', None)
            self.assertEqual(cfg.javinfo_api_url, 'http://127.0.0.1:8080')


from modules.info_client import InfoClient


class InfoClientSupplementProxyTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_info_client_uses_runtime_javinfo_config(self):
        import modules.info_client as info_client

        with patch.dict('os.environ', {'JAVINFO_API_URL': 'http://javinfo.internal:18080'}, clear=False), \
             patch('config.config._config', {'javinfo': {'timeout': 12}}):
            info_client._info_client = None
            client = info_client.get_info_client()

        self.assertEqual(client.api_url, 'http://javinfo.internal:18080')
        self.assertEqual(client.timeout, 12)
        info_client._info_client = None

    async def test_proxy_get_injects_bearer_token(self):
        client = InfoClient()
        fake_response = {"data": [], "total_count": 0}

        with patch.dict('os.environ', {'SUPPLEMENT_ADMIN_TOKEN': 'my-secret'}, clear=False), \
             patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = fake_response
            mock_client.get.return_value = mock_response
            get_client.return_value = mock_client

            result = await client.proxy_get("/api/v1/supplement/stats")

        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", {})
        self.assertEqual(headers.get("Authorization"), "Bearer my-secret")
        self.assertEqual(result, fake_response)

    async def test_proxy_get_no_token_when_empty(self):
        client = InfoClient()
        fake_response = {"data": []}

        with patch.dict('os.environ', {}, clear=False), patch('config.config._config', {}):
            os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
            with patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = fake_response
                mock_client.get.return_value = mock_response
                get_client.return_value = mock_client

                self.assertEqual(await client.proxy_get("/api/v1/supplement/stats"), fake_response)

        headers = mock_client.get.call_args.kwargs.get("headers", {})
        self.assertNotIn("Authorization", headers)

    async def test_proxy_post_injects_bearer_token(self):
        client = InfoClient()
        fake_response = {"job_id": 1, "status": "queued"}

        with patch.dict('os.environ', {'SUPPLEMENT_ADMIN_TOKEN': 'my-secret'}, clear=False), \
             patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_response.json.return_value = fake_response
            mock_client.post.return_value = mock_response
            get_client.return_value = mock_client

            result = await client.proxy_post("/api/v1/supplement/actresses/1/filmography/jobs")

        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", {})
        self.assertEqual(headers.get("Authorization"), "Bearer my-secret")
        self.assertEqual(result, fake_response)

    async def test_proxy_patch_injects_bearer_token(self):
        client = InfoClient()
        fake_response = {"success": True}

        with patch.dict('os.environ', {'SUPPLEMENT_ADMIN_TOKEN': 'my-secret'}, clear=False), \
             patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = fake_response
            mock_client.patch.return_value = mock_response
            get_client.return_value = mock_client

            result = await client.proxy_patch("/api/v1/config", {"proxy_url": "http://proxy"})

        call_args = mock_client.patch.call_args
        headers = call_args.kwargs.get("headers", {})
        self.assertEqual(headers.get("Authorization"), "Bearer my-secret")
        self.assertEqual(result, fake_response)

    async def test_get_actress_videos_passes_include_supplement(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": [{"content_id": "abc"}], "total_count": 1}
            await client.get_actress_videos(
                123, page=1, page_size=20,
                include_supplement="1", service_code="digital", year=2024,
            )

        mock_get.assert_awaited_once_with(
            "/api/v1/actresses/123/videos",
            params={
                "page": 1,
                "page_size": 20,
                "include_supplement": "1",
                "service_code": "digital",
                "year": 2024,
            },
        )

    async def test_list_actresses_passes_valid_avatar_filter(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": [], "total_count": 0}
            await client.list_actresses(page=2, page_size=36, has_valid_avatar=1)

        mock_get.assert_awaited_once_with(
            "/api/v1/actresses",
            params={"page": 2, "page_size": 36, "has_valid_avatar": 1},
        )

    async def test_get_actress_videos_falls_back_when_supplement_result_is_empty(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"data": [], "total_count": 0, "total_pages": 0},
                {"data": [{"content_id": "mrec00002"}], "total_count": 934, "total_pages": 934},
            ]

            result = await client.get_actress_videos(1020504, page=1, page_size=20, include_supplement="1")

        self.assertEqual(result["total_count"], 934)
        self.assertEqual(result["data"][0]["content_id"], "mrec00002")
        self.assertEqual(mock_get.await_count, 2)
        mock_get.assert_any_await(
            "/api/v1/actresses/1020504/videos",
            params={"page": 1, "page_size": 20, "include_supplement": "1"},
        )
        mock_get.assert_any_await(
            "/api/v1/actresses/1020504/videos",
            params={"page": 1, "page_size": 20},
        )

    async def test_get_actress_videos_falls_back_when_supplement_result_has_unknown_total(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"data": [], "total_count": -1, "total_pages": -1},
                {"data": [{"content_id": "mrec00002"}], "total_count": -1, "total_pages": -1},
            ]

            result = await client.get_actress_videos(
                1020504,
                page=1,
                page_size=20,
                include_supplement="1",
                include_total=False,
            )

        self.assertEqual(result["data"][0]["content_id"], "mrec00002")
        self.assertEqual(mock_get.await_count, 2)
        mock_get.assert_any_await(
            "/api/v1/actresses/1020504/videos",
            params={
                "page": 1,
                "page_size": 20,
                "include_total": False,
                "include_supplement": "1",
            },
        )
        mock_get.assert_any_await(
            "/api/v1/actresses/1020504/videos",
            params={"page": 1, "page_size": 20, "include_total": False},
        )

    async def test_get_actress_videos_fallback_preserves_filters(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"data": [], "total_count": 0, "total_pages": 0},
                {"data": [{"content_id": "mrec00002"}], "total_count": 20, "total_pages": 1},
            ]

            result = await client.get_actress_videos(
                1020504,
                page=1,
                page_size=20,
                include_supplement="1",
                service_code="digital",
                year=2026,
                sort_by="release_date:desc",
            )

        self.assertEqual(result["total_count"], 20)
        mock_get.assert_any_await(
            "/api/v1/actresses/1020504/videos",
            params={
                "page": 1,
                "page_size": 20,
                "service_code": "digital",
                "year": 2026,
                "sort_by": "release_date:desc",
            },
        )


from routers import supplement


class SupplementRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_stats_proxies_to_info_client(self):
        fake_stats = {
            "jobs_by_status": {"succeeded": 5},
            "total_movies": 100,
            "matched_r18": 60,
            "supplement_only": 40,
        }
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = fake_stats

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            result = await supplement.supplement_stats()

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/stats", params=None)
        self.assertEqual(result, fake_stats)

    async def test_actress_status_passes_source_param(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"actress_id": 1}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.supplement_actress_status(actress_id=1)

        mock_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/actresses/1/status",
            params={"source": "avbase"},
        )

    async def test_filmography_job_defaults_source_avbase(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 1, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.create_filmography_job(actress_id=1)

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/actresses/1/filmography/jobs",
            params={"source": "avbase"},
        )

    async def test_resolved_refresh_no_params(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"actress_id": 1, "resolved_refreshed": 10}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.refresh_resolved(actress_id=1)

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/actresses/1/resolved/refresh",
            params=None,
        )

    async def test_list_jobs_passes_filters(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"data": [], "total_count": 0}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_jobs(page=2, page_size=50, status="failed", actress_id=123)

        mock_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/jobs",
            params={"page": 2, "page_size": 50, "status": "failed", "actress_id": 123},
        )

    async def test_create_gfriends_avatar_sync_job_proxies_to_info_client(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 9, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            result = await supplement.create_gfriends_avatar_sync_job()

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/avatars/gfriends/jobs",
        )
        self.assertEqual(result, {"job_id": 9, "status": "queued"})

    async def test_retry_job(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 2, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.retry_job(job_id=1)

        mock_client.proxy_post.assert_awaited_once_with("/api/v1/supplement/jobs/1/retry")

    async def test_cancel_job(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 1, "status": "failed"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.cancel_job(job_id=1)

        mock_client.proxy_post.assert_awaited_once_with("/api/v1/supplement/jobs/1/cancel")

    async def test_recover_stale_defaults_30_minutes(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"recovered": 2}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.recover_stale()

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/jobs/recover_stale",
            params={"older_than_minutes": 30},
        )

    async def test_list_movies_passes_filters(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"data": [], "total_count": 0}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_supplement_movies(
                page=1, page_size=20, matched=False, actress_id=456, q="ABP588",
            )

        mock_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/movies",
            params={"page": 1, "page_size": 20, "matched": "false", "actress_id": 456, "q": "ABP588"},
        )

    async def test_list_movies_passes_quality_filters(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"data": [], "total_count": 0}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_supplement_movies(
                page=1,
                page_size=20,
                missing_cover=True,
                missing_runtime=True,
                missing_maker=True,
                missing_categories=True,
                max_completeness=2,
            )

        mock_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/movies",
            params={
                "page": 1,
                "page_size": 20,
                "missing_cover": "true",
                "missing_runtime": "true",
                "missing_maker": "true",
                "missing_categories": "true",
                "max_completeness": 2,
            },
        )

    async def test_get_movie_sources(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"movie": {"id": 12}, "field_values": []}

        with patch("routers.supplement.get_info_client", return_value=mock_client), \
             patch("routers.supplement.get_translator_service") as get_translator:
            translator = AsyncMock()
            translator.translate_supplement_sources.return_value = {"movie": {"id": 12}, "field_values": []}
            get_translator.return_value = translator
            await supplement.get_movie_sources(movie_id=12)

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/movies/12/sources")
        translator.translate_supplement_sources.assert_awaited_once_with(
            {"movie": {"id": 12}, "field_values": []},
            allow_network=False,
        )

    async def test_create_download_candidates_from_supplement_passes_filters(self):
        with patch(
            "routers.supplement.generate_download_candidates_from_supplement",
            new_callable=AsyncMock,
        ) as generate:
            generate.return_value = {"created": 2, "existing": 1, "candidate_count": 3}
            result = await supplement.create_download_candidates_from_supplement(
                actress_id=123,
                actress_name="Actor",
                source="avbase",
                q="SIVR",
                limit=50,
                matched=False,
                missing_cover=True,
                missing_runtime=True,
                missing_maker=True,
                missing_categories=True,
                max_completeness=2,
            )

        generate.assert_awaited_once_with(
            actress_id=123,
            actress_name="Actor",
            supplement_source="avbase",
            q="SIVR",
            limit=50,
            matched=False,
            missing_cover=True,
            missing_runtime=True,
            missing_maker=True,
            missing_categories=True,
            max_completeness=2,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["created"], 2)

    async def test_list_sources(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = [{"source": "avbase"}]

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_sources()

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/sources", params=None)

    async def test_list_sources_health(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = [{"source": "avbase", "runtime_status": "healthy"}]

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_sources_health()

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/sources/health", params=None)

    async def test_source_health_actions(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"source": "javbus", "status": "paused"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.pause_source(source="javbus", body={"reason": "maintenance"})
            await supplement.resume_source(source="javbus")

        self.assertEqual(mock_client.proxy_post.await_args_list[0].args[0], "/api/v1/supplement/sources/javbus/pause")
        self.assertEqual(mock_client.proxy_post.await_args_list[0].kwargs["json_body"], {"reason": "maintenance"})
        self.assertEqual(mock_client.proxy_post.await_args_list[1].args[0], "/api/v1/supplement/sources/javbus/resume")

    async def test_list_source_budgets_proxy(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = [{"source": "fanza", "local_active": 1}]

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_sources_budgets()

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/sources/budgets", params=None)

    async def test_run_provider_smoke_proxy(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"total": 1, "ok": 1, "failed": 0, "reports": []}
        body = {"source": "fc2", "source_movie_id": "FC2-PPV-4897640"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.run_provider_smoke(body=body)

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/providers/smoke",
            json_body=body,
        )

    async def test_list_provider_smoke_runs_proxy(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = [{"id": 1, "ok": 1, "failed": 0}]

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.list_provider_smoke_runs(limit=5, source="fc2")

        mock_client.proxy_get.assert_awaited_once_with(
            "/api/v1/supplement/providers/smoke/runs",
            params={"limit": 5, "source": "fc2"},
        )

    async def test_manual_movie_actions_proxy_json_body(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"supplement_movie_id": 12}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.match_movie(movie_id=12, body={"content_id": "umd1010"})
            await supplement.ignore_movie(movie_id=12, body={"reason": "skip"})
            await supplement.unmatch_movie(movie_id=12, body={"reason": "undo"})

        self.assertEqual(mock_client.proxy_post.await_args_list[0].args[0], "/api/v1/supplement/movies/12/match")
        self.assertEqual(mock_client.proxy_post.await_args_list[0].kwargs["json_body"], {"content_id": "umd1010"})
        self.assertEqual(mock_client.proxy_post.await_args_list[1].args[0], "/api/v1/supplement/movies/12/ignore")
        self.assertEqual(mock_client.proxy_post.await_args_list[1].kwargs["json_body"], {"reason": "skip"})
        self.assertEqual(mock_client.proxy_post.await_args_list[2].args[0], "/api/v1/supplement/movies/12/unmatch")
        self.assertEqual(mock_client.proxy_post.await_args_list[2].kwargs["json_body"], {"reason": "undo"})

    async def test_enrich_movie_detail_queues_job_by_default(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 3, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.enrich_movie_detail(source_movie_id="prestige:SIVR-438", source="avbase")

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": "avbase", "source_movie_id": "prestige:SIVR-438"},
        )

    async def test_enrich_movie_detail_allows_explicit_sync_smoke(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"source": "avbase", "source_movie_id": "prestige:SIVR-438"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.enrich_movie_detail(
                source_movie_id="prestige:SIVR-438",
                source="avbase",
                sync=True,
            )

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail",
            params={"source": "avbase", "source_movie_id": "prestige:SIVR-438"},
        )

    async def test_create_movie_detail_job_passes_source_movie_id(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 3, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.create_movie_detail_job(source_movie_id="prestige:SIVR-438", source="avbase")

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": "avbase", "source_movie_id": "prestige:SIVR-438"},
        )

    async def test_create_movie_detail_job_passes_actress_id(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"job_id": 3, "status": "queued"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.create_movie_detail_job(
                source_movie_id="prestige:SIVR-438",
                source="all",
                actress_id=1098399,
            )

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs",
            params={"source": "all", "source_movie_id": "prestige:SIVR-438", "actress_id": 1098399},
        )

    async def test_create_movie_detail_batch_jobs_passes_filters(self):
        mock_client = AsyncMock()
        mock_client.proxy_post.return_value = {"queued": 2, "existing": 1, "skipped": 0, "job_ids": [1, 2, 3]}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.create_movie_detail_batch_jobs(
                source="avbase",
                limit=20,
                matched=False,
                missing_cover=True,
                max_completeness=2,
            )

        mock_client.proxy_post.assert_awaited_once_with(
            "/api/v1/supplement/movies/detail/jobs/batch",
            params={
                "source": "avbase",
                "limit": 20,
                "matched": "false",
                "missing_cover": "true",
                "max_completeness": 2,
            },
        )

    async def test_get_job_detail(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"id": 1, "status": "succeeded"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.get_job_detail(job_id=1)

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/jobs/1")


if __name__ == '__main__':
    unittest.main()
