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


if __name__ == '__main__':
    unittest.main()
