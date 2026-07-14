from __future__ import annotations

import asyncio
import base64
import hashlib
import tempfile
import threading
import time
import unittest
from concurrent.futures import CancelledError as ConcurrentCancelledError
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx
import yaml


class SequenceHTTPClient:
    def __init__(self, responses: list[Any]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        response = self.responses.pop(0)
        if callable(response):
            response = response(method, url, kwargs)
        return response

    async def aclose(self) -> None:
        return None


class LoopThread:
    def __init__(self, name: str) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name=name, daemon=True)
        self.thread.start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=2)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2)
        self.loop.close()


def response(payload: dict, *, status_code: int = 200, url: str = "https://115.test/api") -> httpx.Response:
    return httpx.Response(
        status_code,
        request=httpx.Request("GET", url),
        json=payload,
    )


class Open115ClientTests(unittest.IsolatedAsyncioTestCase):
    def _config(self, root: Path, section: dict | None = None) -> SimpleNamespace:
        config_path = root / "config.yaml"
        data = {"server": {"port": 18090}, "open115": section or {}}
        config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return SimpleNamespace(_config=data, config_path=config_path)

    async def test_owned_http_clients_are_reused_per_loop_and_closed_on_owner(self):
        from services.open115 import Open115Client

        loops = [LoopThread("open115-a"), LoopThread("open115-b")]
        clients = []

        class RecordingHTTPClient:
            def __init__(self):
                self.created_loop = asyncio.get_running_loop()
                self.request_loops = []
                self.closed_loop = None
                self.is_closed = False

            async def request(self, _method, _url, **_kwargs):
                self.request_loops.append(asyncio.get_running_loop())
                return response({"state": True, "data": {}})

            async def aclose(self):
                self.closed_loop = asyncio.get_running_loop()
                self.is_closed = True

        def factory():
            client = RecordingHTTPClient()
            clients.append(client)
            return client

        try:
            client = Open115Client(http_client_factory=factory, min_request_interval=0)
            loops[0].run(client._request("GET", "https://115.test/a"))
            loops[1].run(client._request("GET", "https://115.test/b"))
            loops[0].run(client._request("GET", "https://115.test/c"))

            self.assertEqual(len(clients), 2)
            self.assertEqual([len(item.request_loops) for item in clients], [2, 1])

            await client.close()
            self.assertTrue(all(item.closed_loop is item.created_loop for item in clients))
        finally:
            for loop in loops:
                loop.stop()

    async def test_injected_http_client_remains_caller_owned(self):
        from services.open115 import Open115Client

        http = SequenceHTTPClient([])
        http.closed = False

        async def record_close():
            http.closed = True

        http.aclose = record_close
        client = Open115Client(http_client=http, min_request_interval=0)
        await client.close()

        self.assertFalse(http.closed)

    async def test_request_slots_are_reserved_globally_across_event_loops(self):
        from services.open115 import Open115Client

        loops = [LoopThread("throttle-a"), LoopThread("throttle-b")]
        barrier = threading.Barrier(2)
        starts = []
        starts_lock = threading.Lock()

        class RecordingHTTPClient:
            async def request(self, _method, _url, **_kwargs):
                with starts_lock:
                    starts.append(time.monotonic())
                return response({"state": True, "data": {}})

        async def request_after_barrier(client, suffix):
            await asyncio.to_thread(barrier.wait)
            return await client._request("GET", f"https://115.test/{suffix}")

        try:
            client = Open115Client(http_client=RecordingHTTPClient(), min_request_interval=0.05)
            futures = [
                asyncio.run_coroutine_threadsafe(request_after_barrier(client, index), loop.loop)
                for index, loop in enumerate(loops)
            ]
            for future in futures:
                future.result(timeout=2)

            self.assertEqual(len(starts), 2)
            self.assertGreaterEqual(abs(starts[1] - starts[0]), 0.04)
        finally:
            for loop in loops:
                loop.stop()

    async def test_device_auth_uses_standard_base64_sha256_pkce(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "uid": "uid-1",
                        "time": "123",
                        "sign": "sig",
                        "qrcode": "qr-content",
                    },
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            with patch("services.open115.secrets.token_urlsafe", return_value="fixed-verifier"):
                result = await client.start_device_auth()

        expected = base64.b64encode(hashlib.sha256(b"fixed-verifier").digest()).decode()
        self.assertEqual(result["uid"], "uid-1")
        self.assertEqual(result["qrcode"], "qr-content")
        self.assertEqual(http.calls[0]["kwargs"]["data"]["code_challenge"], expected)
        self.assertNotIn("-", expected)
        self.assertNotIn("_", expected)

    async def test_confirmed_device_auth_persists_tokens_without_returning_them(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {"uid": "uid-1", "time": "123", "sign": "sig", "qrcode": "qr"},
                }),
                response({"state": 1, "data": {"status": 2}}),
                response({
                    "code": 0,
                    "data": {
                        "access_token": "access-secret",
                        "refresh_token": "refresh-secret",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)
            await client.start_device_auth()

            result = await client.poll_device_auth("uid-1")
            stored = yaml.safe_load(cfg.config_path.read_text(encoding="utf-8"))

        self.assertEqual(result, {"status": "confirmed", "bound": True})
        self.assertEqual(stored["open115"]["access_token"], "access-secret")
        self.assertEqual(stored["open115"]["refresh_token"], "refresh-secret")
        self.assertNotIn("access_token", result)
        self.assertNotIn("refresh_token", result)

    async def test_concurrent_refresh_only_calls_refresh_endpoint_once(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "app_id": "app-123",
                "access_token": "old-access",
                "refresh_token": "old-refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "access_token": "new-access",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            results = await asyncio.gather(
                client.refresh_access_token(expected_access_token="old-access"),
                client.refresh_access_token(expected_access_token="old-access"),
            )

        self.assertEqual(results, [True, True])
        refresh_calls = [call for call in http.calls if call["url"].endswith("/open/refreshToken")]
        self.assertEqual(len(refresh_calls), 1)

    async def test_refresh_singleflight_is_shared_across_event_loops(self):
        from services.open115 import Open115Client

        loops = [LoopThread("refresh-a"), LoopThread("refresh-b")]
        entered = threading.Event()
        release = threading.Event()

        class BlockingHTTPClient:
            def __init__(self):
                self.calls = 0

            async def request(self, _method, _url, **_kwargs):
                self.calls += 1
                entered.set()
                await asyncio.to_thread(release.wait)
                return response({
                    "code": 0,
                    "data": {
                        "access_token": "new-access",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                })

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cfg = self._config(Path(tmp), {
                    "access_token": "old-access",
                    "refresh_token": "old-refresh",
                })
                http = BlockingHTTPClient()
                client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

                first = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"),
                    loops[0].loop,
                )
                self.assertTrue(entered.wait(timeout=1))
                second = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"),
                    loops[1].loop,
                )
                release.set()

                self.assertTrue(first.result(timeout=2))
                self.assertTrue(second.result(timeout=2))
                self.assertEqual(http.calls, 1)
        finally:
            release.set()
            for loop in loops:
                loop.stop()

    async def test_refresh_singleflight_supports_many_cross_loop_followers_without_executor_use(self):
        from services.open115 import Open115Client

        loops = [LoopThread("refresh-many-a"), LoopThread("refresh-many-b")]
        entered = threading.Event()
        release = threading.Event()

        class BlockingHTTPClient:
            def __init__(self):
                self.calls = 0

            async def request(self, _method, _url, **_kwargs):
                self.calls += 1
                entered.set()
                while not release.is_set():
                    await asyncio.sleep(0.005)
                return response({"code": 0, "data": {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 7200,
                }})

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cfg = self._config(Path(tmp), {
                    "access_token": "old-access", "refresh_token": "old-refresh",
                })
                http = BlockingHTTPClient()
                client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)
                callers = [
                    asyncio.run_coroutine_threadsafe(
                        client.refresh_access_token(expected_access_token="old-access"),
                        loops[index % 2].loop,
                    )
                    for index in range(64)
                ]
                self.assertTrue(entered.wait(timeout=1))
                probe = asyncio.run_coroutine_threadsafe(
                    asyncio.to_thread(lambda: 42), loops[1].loop
                )
                self.assertEqual(probe.result(timeout=1), 42)
                release.set()
                self.assertTrue(all(future.result(timeout=2) for future in callers))
                self.assertEqual(http.calls, 1)
        finally:
            release.set()
            for loop in loops:
                loop.stop()

    async def test_cancelling_refresh_follower_does_not_cancel_batch_or_next_refresh(self):
        from services.open115 import Open115Client

        loops = [LoopThread("refresh-cancel-a"), LoopThread("refresh-cancel-b")]
        entered = threading.Event()
        release = threading.Event()

        class BlockingHTTPClient:
            def __init__(self):
                self.calls = 0

            async def request(self, _method, _url, **_kwargs):
                self.calls += 1
                entered.set()
                while not release.is_set():
                    await asyncio.sleep(0.005)
                return response({"code": 0, "data": {
                    "access_token": f"access-{self.calls}",
                    "refresh_token": f"refresh-{self.calls}",
                    "expires_in": 7200,
                }})

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cfg = self._config(Path(tmp), {
                    "access_token": "old-access", "refresh_token": "old-refresh",
                })
                http = BlockingHTTPClient()
                client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)
                leader = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"), loops[0].loop
                )
                self.assertTrue(entered.wait(timeout=1))
                cancelled = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"), loops[1].loop
                )
                survivor = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"), loops[1].loop
                )
                cancelled.cancel()
                release.set()
                self.assertTrue(leader.result(timeout=2))
                self.assertTrue(survivor.result(timeout=2))
                with self.assertRaises(ConcurrentCancelledError):
                    cancelled.result(timeout=2)

                release.clear()
                entered.clear()
                next_refresh = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="access-1"), loops[0].loop
                )
                self.assertTrue(entered.wait(timeout=1))
                release.set()
                self.assertTrue(next_refresh.result(timeout=2))
                self.assertEqual(http.calls, 2)
        finally:
            release.set()
            for loop in loops:
                loop.stop()

    async def test_cancelling_refresh_leader_cancels_followers_and_allows_retry(self):
        from services.open115 import Open115Client

        loops = [LoopThread("refresh-leader-a"), LoopThread("refresh-leader-b")]
        entered = threading.Event()
        release = threading.Event()

        class BlockingHTTPClient:
            def __init__(self):
                self.calls = 0

            async def request(self, _method, _url, **_kwargs):
                self.calls += 1
                entered.set()
                while not release.is_set():
                    await asyncio.sleep(0.005)
                return response({"code": 0, "data": {
                    "access_token": "retry-access", "refresh_token": "retry-refresh",
                }})

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cfg = self._config(Path(tmp), {
                    "access_token": "old-access", "refresh_token": "old-refresh",
                })
                http = BlockingHTTPClient()
                client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)
                leader = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"), loops[0].loop
                )
                self.assertTrue(entered.wait(timeout=1))
                followers = [
                    asyncio.run_coroutine_threadsafe(
                        client.refresh_access_token(expected_access_token="old-access"), loops[1].loop
                    )
                    for _ in range(4)
                ]
                leader.cancel()
                with self.assertRaises(ConcurrentCancelledError):
                    leader.result(timeout=2)
                for follower in followers:
                    with self.assertRaises(ConcurrentCancelledError):
                        follower.result(timeout=2)

                entered.clear()
                release.set()
                retry = asyncio.run_coroutine_threadsafe(
                    client.refresh_access_token(expected_access_token="old-access"), loops[1].loop
                )
                self.assertTrue(retry.result(timeout=2))
                self.assertEqual(http.calls, 2)
        finally:
            release.set()
            for loop in loops:
                loop.stop()

    async def test_auth_request_retries_once_after_expired_token(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "app_id": "app-123",
                "access_token": "old-access",
                "refresh_token": "old-refresh",
            })
            http = SequenceHTTPClient([
                response({"state": False, "code": 99, "message": "expired"}),
                response({
                    "code": 0,
                    "data": {
                        "access_token": "new-access",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                }),
                response({"state": True, "data": {"user_id": "42"}}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            user = await client.user_info()

        self.assertEqual(user["user_id"], "42")
        self.assertEqual(http.calls[0]["kwargs"]["headers"]["Authorization"], "Bearer old-access")
        self.assertEqual(http.calls[2]["kwargs"]["headers"]["Authorization"], "Bearer new-access")

    async def test_import_refresh_token_refreshes_and_keeps_status_sanitized(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"app_id": "app-123"})
            http = SequenceHTTPClient([
                response({
                    "code": 0,
                    "data": {
                        "access_token": "access-secret",
                        "refresh_token": "rotated-secret",
                        "expires_in": 7200,
                    },
                }),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            result = await client.import_refresh_token("imported-secret")
            status = client.status()

        self.assertEqual(result, {"bound": True})
        self.assertTrue(status["bound"])
        self.assertFalse(status["verified"])
        self.assertNotIn("access_token", status)
        self.assertNotIn("refresh_token", status)
        self.assertNotIn("imported-secret", repr(status))

    async def test_connection_success_marks_current_binding_verified(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
                "verified": False,
            })
            http = SequenceHTTPClient([
                response({"state": True, "data": {"user_id": "42", "user_name": "JavHub"}}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            result = await client.test_connection()

        self.assertTrue(result["ok"])
        self.assertTrue(client.status()["verified"])

    async def test_connection_failure_clears_previous_verification(self):
        from services.open115 import Open115Client, Open115Error

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
                "verified": True,
            })
            http = SequenceHTTPClient([
                response({"state": False, "code": 500, "message": "offline"}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            with self.assertRaises(Open115Error):
                await client.test_connection()

        self.assertFalse(client.status()["verified"])

    async def test_environment_managed_refresh_token_cannot_be_unbound_by_config(self):
        from services.open115 import Open115Client, Open115Error

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "refresh_token": "config-refresh",
                "verified": True,
            })
            client = Open115Client(
                config_obj=cfg,
                http_client=SequenceHTTPClient([]),
                min_request_interval=0,
            )

            with patch.dict("os.environ", {"OPEN115_REFRESH_TOKEN": "environment-refresh"}):
                with self.assertRaisesRegex(Open115Error, "环境变量"):
                    client.unbind()

            stored = yaml.safe_load(cfg.config_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["open115"]["refresh_token"], "config-refresh")

    async def test_downurl_forwards_exact_final_player_user_agent(self):
        from services.open115 import Open115Client

        player_ua = "Infuse/8.1 AppleTV"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "state": True,
                    "data": {
                        "123": {
                            "pick_code": "pick",
                            "url": {"url": "https://download.115.test/file?sig=secret"},
                        }
                    },
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            url = await client.downurl("pick", player_ua)

        self.assertEqual(url, "https://download.115.test/file?sig=secret")
        self.assertEqual(http.calls[0]["kwargs"]["headers"]["User-Agent"], player_ua)

    async def test_offline_submission_uses_newline_urls_and_target_folder(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "state": True,
                    "data": [
                        {"state": True, "info_hash": "hash-a"},
                        {"state": True, "info_hash": "hash-b"},
                    ],
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            hashes = await client.add_offline_task(["magnet:a", "magnet:b"], "folder-1")

        self.assertEqual(hashes, ["hash-a", "hash-b"])
        self.assertEqual(http.calls[0]["kwargs"]["data"], {
            "urls": "magnet:a\nmagnet:b",
            "wp_path_id": "folder-1",
        })

    async def test_offline_quota_backfills_remain_when_absent(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([
                response({"state": True, "data": {"total": 1500, "used": 200}}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            quota = await client.offline_quota()

        self.assertEqual(quota, {"total": 1500, "used": 200, "remain": 1300})

    async def test_offline_quota_reads_explicit_remain(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([
                response({"state": True, "data": {"count": 1500, "used": 200, "remain": 999}}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            quota = await client.offline_quota()

        self.assertEqual(quota["remain"], 999)

    async def test_delete_offline_task_posts_info_hash_and_source_flag(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([response({"state": True})])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            await client.delete_offline_task("hash-a", del_source=True)

        self.assertTrue(http.calls[0]["url"].endswith("/open/offline/del_task"))
        self.assertEqual(
            http.calls[0]["kwargs"]["data"],
            {"info_hash": "hash-a", "del_source_file": 1},
        )

    async def test_clear_offline_tasks_posts_flag(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([response({"state": True})])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            await client.clear_offline_tasks(2)

        self.assertTrue(http.calls[0]["url"].endswith("/open/offline/clear_task"))
        self.assertEqual(http.calls[0]["kwargs"]["data"], {"flag": 2})

    async def test_list_folder_forwards_sort_params(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([
                response({"state": True, "data": [], "path": [], "count": 0}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            await client.list_folder("7", offset=0, limit=50, order="file_size", asc=1)

        params = http.calls[0]["kwargs"]["params"]
        self.assertEqual(params["o"], "file_size")
        self.assertEqual(params["asc"], 1)
        self.assertEqual(params["cid"], "7")

    async def test_list_folder_omits_sort_params_when_unset(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {"access_token": "access", "refresh_token": "refresh"})
            http = SequenceHTTPClient([
                response({"state": True, "data": [], "path": [], "count": 0}),
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            await client.list_folder("0")

        params = http.calls[0]["kwargs"]["params"]
        self.assertNotIn("o", params)
        self.assertNotIn("asc", params)

    async def test_transcode_urls_are_sorted_by_definition(self):
        from services.open115 import Open115Client

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(Path(tmp), {
                "access_token": "access",
                "refresh_token": "refresh",
            })
            http = SequenceHTTPClient([
                response({
                    "state": True,
                    "data": {
                        "video_url": [
                            {"url": "https://hls/720.m3u8", "definition": 3, "desc": "720p"},
                            {"url": "https://hls/4k.m3u8", "definition": 5, "desc": "4k"},
                        ]
                    },
                })
            ])
            client = Open115Client(config_obj=cfg, http_client=http, min_request_interval=0)

            urls = await client.video_transcode_urls("pick")

        self.assertEqual([item.definition for item in urls], [5, 3])
        self.assertEqual(http.calls[0]["kwargs"]["params"], {"pick_code": "pick"})


if __name__ == "__main__":
    unittest.main()
