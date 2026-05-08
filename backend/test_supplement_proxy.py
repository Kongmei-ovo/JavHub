from __future__ import annotations
import unittest
from unittest.mock import patch


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


import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from modules.info_client import InfoClient


class InfoClientSupplementProxyTest(unittest.IsolatedAsyncioTestCase):
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

        with patch.dict('os.environ', {}, clear=False):
            os.environ.pop('SUPPLEMENT_ADMIN_TOKEN', None)
            with patch.object(client, "_get_client", new_callable=AsyncMock) as get_client:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = fake_response
                mock_client.get.return_value = mock_response
                get_client.return_value = mock_client

                result = await client.proxy_get("/api/v1/supplement/stats")

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

    async def test_get_actress_videos_passes_include_supplement(self):
        client = InfoClient()

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": [], "total_count": 0}
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

    async def test_get_job_detail(self):
        mock_client = AsyncMock()
        mock_client.proxy_get.return_value = {"id": 1, "status": "succeeded"}

        with patch("routers.supplement.get_info_client", return_value=mock_client):
            await supplement.get_job_detail(job_id=1)

        mock_client.proxy_get.assert_awaited_once_with("/api/v1/supplement/jobs/1")


if __name__ == '__main__':
    unittest.main()
