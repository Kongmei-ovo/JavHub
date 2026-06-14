from __future__ import annotations

import unittest

from test_support.client import create_authed_router_test_client, create_router_test_client
from test_support.postgres import TempPostgresMixin


class PlaybackAuthTests(TempPostgresMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from services.emby_auth import clear_compat_sessions

        clear_compat_sessions()  # no session bleed between cases

    def _unauthed(self, router):
        return create_router_test_client(router)

    def test_stream_requires_auth(self):
        from routers.playback import router

        resp = self._unauthed(router).get("/api/v1/playback/resources/1/stream")
        self.assertIn(resp.status_code, (401, 403))

    def test_valid_header_token_passes_auth(self):
        from routers.playback import router

        # Authed client carries X-Emby-Token; auth passes → 404 (resource missing),
        # not 401. Getting past auth is the assertion.
        resp = create_authed_router_test_client(router).get("/api/v1/playback/resources/1/stream")
        self.assertNotIn(resp.status_code, (401, 403))

    def test_valid_query_token_passes_auth_for_hls_subrequests(self):
        from config import config
        from routers.playback import router
        from services.emby_auth import issue_token

        token = issue_token(config.emby_compat_username, config.emby_compat_password)
        # HLS sub-requests are browser-issued and can only carry the token in the
        # query string — that path must authenticate too.
        resp = self._unauthed(router).get(
            f"/api/v1/playback/resources/1/hls/no-session/master.m3u8?token={token}"
        )
        self.assertNotIn(resp.status_code, (401, 403))  # 410 expired session, but authed

    def test_acquisition_endpoints_require_auth(self):
        from routers.acquisitions import router

        resp = self._unauthed(router).post("/api/v1/movies/ABC-1/acquisitions", json={})
        self.assertIn(resp.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
