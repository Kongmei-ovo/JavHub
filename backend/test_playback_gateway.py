from __future__ import annotations

import re
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from test_support.client import create_authed_router_test_client


RESOURCE = {
    "id": 9,
    "movie_id": "stable:item-1",
    "provider": "open115",
    "remote_file_id": "file-1",
    "pick_code": "pick-1",
    "name": "movie.mkv",
    "extension": "mkv",
    "resource_type": "video",
    "status": "ready",
    "is_default": 1,
}


class PlaybackContextTests(unittest.TestCase):
    def test_auto_policy_is_endpoint_and_container_aware(self):
        from services.playback_gateway import PlaybackContext

        web_mkv = PlaybackContext.build(
            user_agent="Mozilla/5.0 Chrome/140",
            accept="video/*",
            mode="auto",
            extension="mkv",
        )
        web_mp4 = PlaybackContext.build(
            user_agent="Mozilla/5.0 Chrome/140",
            accept="video/*",
            mode="auto",
            extension="mp4",
        )
        emby_mkv = PlaybackContext.build(
            user_agent="Emby/4.9",
            accept="*/*",
            mode="auto",
            extension="mkv",
        )
        infuse_mkv = PlaybackContext.build(
            user_agent="Infuse/8.1",
            accept="*/*",
            mode="auto",
            extension="mkv",
        )

        self.assertEqual(web_mkv.preferred_mode, "hls")
        self.assertEqual(web_mp4.preferred_mode, "original")
        self.assertEqual(emby_mkv.preferred_mode, "original")
        self.assertEqual(infuse_mkv.preferred_mode, "original")

    def test_explicit_mode_overrides_auto_policy(self):
        from services.playback_gateway import PlaybackContext

        context = PlaybackContext.build(
            user_agent="Mozilla/5.0",
            accept="video/*",
            mode="original",
            extension="iso",
        )

        self.assertEqual(context.preferred_mode, "original")


class PlaybackResourceRouteTests(unittest.TestCase):
    def _client(self):
        from routers.playback import router

        return create_authed_router_test_client(router)

    def test_original_stream_uses_exact_final_request_user_agent_and_redirects(self):
        player_ua = "IINA/1.4.0 macOS"
        downurl = AsyncMock(return_value="https://download.115.test/file?sig=secret")

        with patch("routers.playback.get_movie_resource", return_value=RESOURCE), \
             patch("routers.playback.open115_client.downurl", new=downurl):
            response = self._client().get(
                "/api/v1/playback/resources/9/stream?mode=auto",
                headers={"User-Agent": player_ua, "Accept": "*/*"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://download.115.test/file?sig=secret")
        self.assertEqual(response.headers["cache-control"], "no-store")
        downurl.assert_awaited_once_with("pick-1", player_ua)

    def test_expired_direct_link_transparently_relinks(self):
        from routers.playback import relink_limiter
        from services.open115 import Open115Error

        relink_limiter.reset()
        # request 1 → link-a; request 2 → first downurl expired, relink → link-b
        downurl = AsyncMock(side_effect=["http://link-a", Open115Error(None, "expired"), "http://link-b"])
        with patch("routers.playback.get_movie_resource", return_value=RESOURCE), \
             patch("routers.playback.open115_client.downurl", new=downurl):
            first = self._client().get("/api/v1/playback/resources/9/stream?mode=original")
            second = self._client().get("/api/v1/playback/resources/9/stream?mode=original")

        self.assertEqual(first.status_code, 302)
        self.assertEqual(first.headers["location"], "http://link-a")
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second.headers["location"], "http://link-b")  # relinked, not an error
        self.assertEqual(downurl.await_count, 3)

    def test_relink_is_capped_and_marks_resource_missing(self):
        from routers.playback import _RELINK_CAP, relink_limiter
        from services.open115 import Open115Error

        relink_limiter.reset()
        downurl = AsyncMock(side_effect=Open115Error(None, "gone"))
        with patch("routers.playback.get_movie_resource", return_value=RESOURCE), \
             patch("routers.playback.open115_client.downurl", new=downurl), \
             patch("routers.playback.set_movie_resource_status") as set_status:
            response = self._client().get("/api/v1/playback/resources/9/stream?mode=original")

        self.assertEqual(response.status_code, 502)
        self.assertLessEqual(downurl.await_count, _RELINK_CAP + 1)  # bounded, no infinite loop
        set_status.assert_called_once_with(9, "missing")

    def test_subtitle_resource_served_as_converted_vtt(self):
        sub = {"id": 12, "resource_type": "subtitle", "movie_id": "ABC-123",
               "pick_code": "pc", "extension": "srt", "name": "ABC-123.srt", "status": "ready"}
        upstream = SimpleNamespace(status_code=200, text="1\n00:00:01,000 --> 00:00:02,000\nHi\n")
        with patch("routers.playback.get_movie_resource", return_value=sub), \
             patch("routers.playback.open115_client.downurl", new=AsyncMock(return_value="http://115/x.srt")), \
             patch("routers.playback.playback_hls_client.get", new=AsyncMock(return_value=upstream)):
            resp = self._client().get("/api/v1/playback/resources/12/subtitle.vtt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"].split(";")[0], "text/vtt")
        self.assertTrue(resp.text.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:02.000", resp.text)

    def test_non_subtitle_resource_rejected_by_subtitle_endpoint(self):
        with patch("routers.playback.get_movie_resource", return_value={"id": 1, "resource_type": "video"}):
            resp = self._client().get("/api/v1/playback/resources/1/subtitle.vtt")
        self.assertEqual(resp.status_code, 404)

    def test_web_mkv_gets_same_origin_hls_redirect_without_upstream_url(self):
        from services.open115 import TranscodeURL

        transcodes = AsyncMock(return_value=[
            TranscodeURL("https://hls.115.test/master.m3u8?sig=secret", 5, "4k")
        ])
        with patch("routers.playback.get_movie_resource", return_value=RESOURCE), \
             patch("routers.playback.open115_client.video_transcode_urls", new=transcodes):
            response = self._client().get(
                "/api/v1/playback/resources/9/stream?mode=auto",
                headers={"User-Agent": "Mozilla/5.0 Chrome/140", "Accept": "video/*"},
            )

        self.assertEqual(response.status_code, 307)
        location = response.headers["location"]
        self.assertIn("/api/v1/playback/resources/9/hls/", location)
        self.assertNotIn("115.test", location)
        self.assertNotIn("sig=", location)

    def test_original_failure_falls_back_to_hls_in_auto_mode(self):
        from services.open115 import Open115Error, TranscodeURL

        with patch("routers.playback.get_movie_resource", return_value={**RESOURCE, "extension": "mp4"}), \
             patch(
                 "routers.playback.open115_client.downurl",
                 new=AsyncMock(side_effect=Open115Error(500, "failed")),
             ), \
             patch(
                 "routers.playback.open115_client.video_transcode_urls",
                 new=AsyncMock(return_value=[
                     TranscodeURL("https://hls.115.test/master.m3u8?sig=secret", 3, "720p")
                 ]),
             ):
            response = self._client().get(
                "/api/v1/playback/resources/9/stream?mode=auto",
                headers={"User-Agent": "Mozilla/5.0 Chrome/140"},
            )

        self.assertEqual(response.status_code, 307)
        self.assertNotIn("115.test", response.headers["location"])

    def test_hls_not_ready_returns_retryable_error(self):
        with patch("routers.playback.get_movie_resource", return_value=RESOURCE), \
             patch(
                 "routers.playback.open115_client.video_transcode_urls",
                 new=AsyncMock(return_value=[]),
             ):
            response = self._client().get(
                "/api/v1/playback/resources/9/stream?mode=hls",
                headers={"User-Agent": "Mozilla/5.0 Chrome/140"},
            )

        self.assertEqual(response.status_code, 425)
        self.assertEqual(response.headers["retry-after"], "15")

    def test_unready_or_non_video_resource_is_rejected_before_resolver(self):
        downurl = AsyncMock()
        with patch(
            "routers.playback.get_movie_resource",
            return_value={**RESOURCE, "resource_type": "subtitle"},
        ), patch("routers.playback.open115_client.downurl", new=downurl):
            response = self._client().get("/api/v1/playback/resources/9/stream")

        self.assertEqual(response.status_code, 409)
        downurl.assert_not_awaited()


class HLSProxyTests(unittest.TestCase):
    def _client(self):
        from routers.playback import router

        return create_authed_router_test_client(router)

    def test_manifest_rewrites_segments_and_key_to_opaque_same_origin_targets(self):
        from services.playback_gateway import hls_sessions

        session_id = hls_sessions.create(
            resource_id=9,
            root_url="https://hls.115.test/path/master.m3u8?sig=secret",
            user_agent="Mozilla/5.0",
        )
        upstream = SimpleNamespace(
            status_code=200,
            content=(
                b'#EXTM3U\n'
                b'#EXT-X-KEY:METHOD=AES-128,URI="key.bin?sig=key-secret"\n'
                b'#EXTINF:5,\n'
                b'segment-1.ts?sig=segment-secret\n'
            ),
            headers={"content-type": "application/vnd.apple.mpegurl"},
        )

        with patch("routers.playback.playback_hls_client.get", new=AsyncMock(return_value=upstream)):
            response = self._client().get(
                f"/api/v1/playback/resources/9/hls/{session_id}/master.m3u8"
            )

        text = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(text.startswith("#EXTM3U"))
        self.assertNotIn("hls.115.test", text)
        self.assertNotIn("key-secret", text)
        self.assertNotIn("segment-secret", text)
        self.assertGreaterEqual(len(re.findall(r"/hls/.+?/", text)), 2)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unknown_hls_session_returns_gone(self):
        response = self._client().get(
            "/api/v1/playback/resources/9/hls/not-a-session/master.m3u8"
        )
        self.assertEqual(response.status_code, 410)

    def test_segment_proxy_preserves_partial_content_status_and_range_headers(self):
        from services.playback_gateway import hls_sessions

        session_id = hls_sessions.create(
            resource_id=9,
            root_url="https://hls.115.test/path/master.m3u8?sig=secret",
            user_agent="IINA/1.4",
        )
        session = hls_sessions.get(session_id, 9)
        target_token = hls_sessions.register_target(
            session,
            "https://hls.115.test/path/segment.ts?sig=secret",
        )
        upstream = SimpleNamespace(
            status_code=206,
            content=b"partial-segment",
            headers={
                "content-type": "video/mp2t",
                "content-range": "bytes 0-14/100",
                "accept-ranges": "bytes",
            },
        )
        upstream_get = AsyncMock(return_value=upstream)

        with patch("routers.playback.playback_hls_client.get", new=upstream_get):
            response = self._client().get(
                f"/api/v1/playback/resources/9/hls/{session_id}/{target_token}",
                headers={"Range": "bytes=0-14"},
            )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers["content-range"], "bytes 0-14/100")
        self.assertEqual(response.headers["accept-ranges"], "bytes")
        upstream_get.assert_awaited_once()
        self.assertEqual(upstream_get.await_args.kwargs["headers"]["Range"], "bytes=0-14")


if __name__ == "__main__":
    unittest.main()
