from __future__ import annotations

import asyncio
import inspect
import unittest
from collections import defaultdict, deque
from types import SimpleNamespace
from typing import Optional, get_type_hints
from unittest.mock import patch

from services import cf_solver


SOLVER_URL = "http://flare.test/v1"
PAGE_URL = "https://jable.tv/videos/test/"
PAGE_HTML = "<html><body>same solved page</body></html>"


class FakeResponse:
    def __init__(self, data: dict, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def json(self) -> dict:
        return self._data


class MalformedResponse(FakeResponse):
    def __init__(self, status_code: int = 200):
        super().__init__({}, status_code=status_code)

    def json(self) -> dict:
        raise ValueError("malformed JSON")


class FakeFlareSolverr:
    def __init__(self):
        self.calls: list[dict] = []
        self.client_timeouts: list[float] = []
        self.existing = False
        self.response_html = PAGE_HTML
        self._responses: dict[str, deque] = defaultdict(deque)
        self.on_client_created = None

    def queue(self, command: str, *responses) -> None:
        self._responses[command].extend(responses)

    def client(self, **kwargs):
        self.client_timeouts.append(kwargs.get("timeout"))
        if self.on_client_created is not None:
            self.on_client_created(len(self.client_timeouts))
        server = self

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def post(self, url: str, *, json: dict):
                return await server.post(url, json)

        return Client()

    async def post(self, url: str, payload: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": dict(payload)})
        command = payload["cmd"]
        if self._responses[command]:
            queued = self._responses[command].popleft()
            response = await queued(payload) if callable(queued) else queued
            self._update_session_state(command, response)
            return response

        if command == "sessions.list":
            sessions = [cf_solver._SESSION_ID] if self.existing else []
            return FakeResponse({"status": "ok", "sessions": sessions})
        if command == "sessions.create":
            self.existing = True
            return FakeResponse({"status": "ok"})
        if command == "sessions.destroy":
            self.existing = False
            return FakeResponse({"status": "ok"})
        if command == "request.get":
            if not self.existing:
                return FakeResponse(
                    {"status": "error", "message": "The session does not exist"}
                )
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": self.response_html},
                }
            )
        raise AssertionError(f"Unexpected FlareSolverr command: {command}")

    def _update_session_state(self, command: str, response: FakeResponse) -> None:
        try:
            data = response.json()
        except (TypeError, ValueError):
            return
        message = str(data.get("message") or "").lower()
        if command == "sessions.create" and data.get("status") == "ok":
            self.existing = True
        elif command == "sessions.destroy" and (
            data.get("status") == "ok" or "session" in message
        ):
            self.existing = False

    def commands(self) -> list[str]:
        return [call["json"]["cmd"] for call in self.calls]


class Clock:
    def __init__(self, now: float = 1_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SessionManagerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = FakeFlareSolverr()
        self.clock = Clock()
        self.manager = cf_solver._SessionManager(monotonic=self.clock)
        self.config_patch = patch.object(
            cf_solver,
            "Config",
            return_value=SimpleNamespace(stream_cf_solver_url=SOLVER_URL),
        )
        self.client_patch = patch.object(
            cf_solver.httpx,
            "AsyncClient",
            side_effect=self.server.client,
        )
        self.config_patch.start()
        self.client_patch.start()

    async def asyncTearDown(self):
        await self.manager.close()
        self.client_patch.stop()
        self.config_patch.stop()

    async def test_start_only_lists_sessions_and_starts_reaper(self):
        sleep_started = asyncio.Event()
        hold_sleep = asyncio.Event()
        sleep_calls: list[float] = []

        async def record_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            sleep_started.set()
            await hold_sleep.wait()

        with patch.object(cf_solver.asyncio, "sleep", side_effect=record_sleep):
            await self.manager.start()
            await sleep_started.wait()

            self.assertEqual(cf_solver._REAPER_INTERVAL_SECONDS, 60)
            self.assertEqual(sleep_calls, [60])
            self.assertEqual(self.server.commands(), ["sessions.list"])
            self.assertNotIn("sessions.create", self.server.commands())
            self.assertNotIn("request.get", self.server.commands())
            self.assertIsNotNone(self.manager.reaper_task)
            self.assertFalse(self.manager.reaper_task.done())

            await self.manager.close()

    async def test_uses_literal_fixed_session_id(self):
        self.assertEqual(cf_solver._SESSION_ID, "javhub-default")

    async def test_start_recognizes_existing_fixed_session(self):
        self.server.existing = True

        await self.manager.start()

        self.assertTrue(self.manager.created)
        self.assertEqual(self.server.calls[0]["json"], {"cmd": "sessions.list"})

    async def test_reaper_completes_interval_without_keepalive_requests(self):
        self.server.existing = True
        second_sleep_started = asyncio.Event()
        hold_second_sleep = asyncio.Event()
        sleep_calls: list[float] = []

        async def complete_one_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            if len(sleep_calls) == 1:
                return
            second_sleep_started.set()
            await hold_second_sleep.wait()

        with patch.object(cf_solver.asyncio, "sleep", side_effect=complete_one_sleep):
            await self.manager.start()
            await second_sleep_started.wait()

            self.assertEqual(sleep_calls, [60, 60])
            self.assertEqual(self.server.commands(), ["sessions.list"])
            self.assertNotIn("sessions.create", self.server.commands())
            self.assertNotIn("request.get", self.server.commands())
            self.assertNotIn("sessions.destroy", self.server.commands())

            await self.manager.close()

    async def test_public_fetch_signature_and_return_contract(self):
        signature = inspect.signature(cf_solver.fetch_with_cf_solver)
        parameters = signature.parameters

        self.assertEqual(list(parameters), ["url", "referer", "timeout_ms"])
        self.assertIs(parameters["url"].default, inspect.Parameter.empty)
        self.assertEqual(parameters["url"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(parameters["referer"].default, "")
        self.assertEqual(parameters["referer"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(parameters["timeout_ms"].default, 60_000)
        self.assertEqual(parameters["timeout_ms"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(
            get_type_hints(cf_solver.fetch_with_cf_solver)["return"],
            Optional[str],
        )

    async def test_first_fetch_creates_session_and_second_fetch_reuses_it(self):
        first = await self.manager.fetch(
            PAGE_URL,
            referer="https://jable.tv/",
            timeout_ms=60_000,
        )
        second = await self.manager.fetch(PAGE_URL)

        self.assertEqual((first, second), (PAGE_HTML, PAGE_HTML))
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "request.get", "request.get"],
        )
        request_payload = self.server.calls[1]["json"]
        self.assertEqual(request_payload["url"], PAGE_URL)
        self.assertEqual(request_payload["maxTimeout"], 60_000)
        self.assertEqual(request_payload["headers"], {"Referer": "https://jable.tv/"})
        self.assertEqual(request_payload["session"], cf_solver._SESSION_ID)
        self.assertEqual(self.server.client_timeouts[0], 70.0)

    async def test_concurrent_cold_fetches_create_session_once(self):
        create_started = asyncio.Event()
        release_create = asyncio.Event()
        second_client_started = asyncio.Event()

        async def block_first_create(_payload):
            create_started.set()
            await release_create.wait()
            return FakeResponse({"status": "ok"})

        def observe_client_count(count: int) -> None:
            if count == 2:
                second_client_started.set()

        self.server.queue("sessions.create", block_first_create)
        self.server.on_client_created = observe_client_count

        first_fetch = asyncio.create_task(
            self.manager.fetch(f"{PAGE_URL}?request=1")
        )
        await create_started.wait()
        second_fetch = asyncio.create_task(
            self.manager.fetch(f"{PAGE_URL}?request=2")
        )
        await second_client_started.wait()

        self.assertFalse(first_fetch.done())
        self.assertFalse(second_fetch.done())
        self.assertEqual(self.server.commands(), ["sessions.create"])

        release_create.set()
        results = await asyncio.gather(first_fetch, second_fetch)

        self.assertEqual(results, [PAGE_HTML, PAGE_HTML])
        self.assertEqual(self.server.commands().count("sessions.create"), 1)
        self.assertEqual(self.server.commands().count("request.get"), 2)

    async def test_session_create_failure_returns_none_without_request(self):
        self.server.queue(
            "sessions.create",
            FakeResponse({"status": "error", "message": "browser unavailable"}),
        )

        result = await self.manager.fetch(PAGE_URL)

        self.assertIsNone(result)
        self.assertFalse(self.manager.created)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertEqual(self.server.commands(), ["sessions.create"])
        self.assertNotIn("request.get", self.server.commands())

    async def test_stale_session_loss_does_not_invalidate_new_generation(self):
        request_started = {"a": asyncio.Event(), "b": asyncio.Event()}
        release_request = {"a": asyncio.Event(), "b": asyncio.Event()}

        async def delayed_session_loss(payload):
            request_name = payload["url"].rsplit("=", 1)[1]
            request_started[request_name].set()
            await release_request[request_name].wait()
            return FakeResponse(
                {"status": "error", "message": "The session does not exist"}
            )

        self.server.queue(
            "request.get",
            delayed_session_loss,
            delayed_session_loss,
        )

        fetch_a = asyncio.create_task(self.manager.fetch(f"{PAGE_URL}?request=a"))
        await request_started["a"].wait()
        fetch_b = asyncio.create_task(self.manager.fetch(f"{PAGE_URL}?request=b"))
        await request_started["b"].wait()
        self.assertEqual(self.manager.active_requests, 2)

        release_request["a"].set()
        result_a = await fetch_a
        self.assertEqual(result_a, PAGE_HTML)
        self.assertEqual(self.server.commands().count("sessions.create"), 2)

        release_request["b"].set()
        result_b = await fetch_b

        self.assertEqual((result_a, result_b), (PAGE_HTML, PAGE_HTML))
        self.assertEqual(self.server.commands().count("request.get"), 4)
        self.assertEqual(self.server.commands().count("sessions.create"), 2)
        self.assertEqual(self.manager.active_requests, 0)

    async def test_reaper_does_not_destroy_before_ttl_or_while_request_active(self):
        await self.manager.fetch(PAGE_URL)

        self.clock.advance(cf_solver._IDLE_TTL_SECONDS - 1)
        await self.manager._reap_if_idle()
        self.assertNotIn("sessions.destroy", self.server.commands())

        both_requests_started = asyncio.Event()
        release_requests = {1: asyncio.Event(), 2: asyncio.Event()}
        request_count = 0

        async def block_request(payload):
            nonlocal request_count
            request_count += 1
            if request_count == 2:
                both_requests_started.set()
            request_number = int(payload["url"].rsplit("=", 1)[1])
            await release_requests[request_number].wait()
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": PAGE_HTML},
                }
            )

        self.server.queue("request.get", block_request, block_request)
        active_fetches = [
            asyncio.create_task(self.manager.fetch(f"{PAGE_URL}?active=1")),
            asyncio.create_task(self.manager.fetch(f"{PAGE_URL}?active=2")),
        ]
        await both_requests_started.wait()
        self.assertEqual(self.manager.active_requests, 2)

        self.clock.advance(cf_solver._IDLE_TTL_SECONDS + 1)
        await self.manager._reap_if_idle()
        self.assertNotIn("sessions.destroy", self.server.commands())

        release_requests[1].set()
        self.assertEqual(await active_fetches[0], PAGE_HTML)
        self.assertEqual(self.manager.active_requests, 1)

        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        await self.manager._reap_if_idle()
        self.assertNotIn("sessions.destroy", self.server.commands())

        release_requests[2].set()
        self.assertEqual(await active_fetches[1], PAGE_HTML)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertEqual(self.manager.last_used_at, self.clock.now)

    async def test_fetch_waits_for_idle_destroy_then_recreates_session(self):
        await self.manager.fetch(PAGE_URL)
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        destroy_started = asyncio.Event()
        release_destroy = asyncio.Event()

        async def block_destroy(_payload):
            destroy_started.set()
            await release_destroy.wait()
            return FakeResponse({"status": "ok"})

        self.server.queue("sessions.destroy", block_destroy)
        reap_task = asyncio.create_task(self.manager._reap_if_idle())
        await destroy_started.wait()

        fetch_client_started = asyncio.Event()
        self.server.on_client_created = lambda _count: fetch_client_started.set()
        fetch_task = asyncio.create_task(self.manager.fetch(f"{PAGE_URL}?after-idle=1"))
        await fetch_client_started.wait()

        self.assertFalse(fetch_task.done())
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "request.get", "sessions.destroy"],
        )

        release_destroy.set()
        await reap_task
        self.assertEqual(await fetch_task, PAGE_HTML)
        self.assertTrue(self.manager.created)
        self.assertEqual(
            self.server.commands(),
            [
                "sessions.create",
                "request.get",
                "sessions.destroy",
                "sessions.create",
                "request.get",
            ],
        )

    async def test_close_waits_for_blocked_fetch_then_destroys_without_recreate(self):
        request_started = asyncio.Event()
        release_request = asyncio.Event()

        async def block_success(_payload):
            request_started.set()
            await release_request.wait()
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": PAGE_HTML},
                }
            )

        self.server.queue("request.get", block_success)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await request_started.wait()
        close_task = asyncio.create_task(self.manager.close())

        try:
            await asyncio.sleep(0)
            self.assertFalse(close_task.done())
            self.assertNotIn("sessions.destroy", self.server.commands())
        finally:
            release_request.set()
            fetch_result = await fetch_task
            await close_task

        self.assertEqual(fetch_result, PAGE_HTML)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertFalse(self.manager.created)
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "request.get", "sessions.destroy"],
        )

        calls_after_close = list(self.server.calls)
        self.assertIsNone(await self.manager.fetch(f"{PAGE_URL}?after-close=1"))
        self.assertEqual(self.server.calls, calls_after_close)

    async def test_cancelled_fetch_finishes_release_cleanup_before_propagating(self):
        request_started = asyncio.Event()
        release_response = asyncio.Event()

        async def block_success(_payload):
            request_started.set()
            await release_response.wait()
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": PAGE_HTML},
                }
            )

        self.server.queue("request.get", block_success)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await asyncio.wait_for(request_started.wait(), timeout=1.0)
        await asyncio.wait_for(self.manager.lock.acquire(), timeout=1.0)
        fetch_outcome = []

        try:
            release_response.set()
            await asyncio.sleep(0)
            self.assertFalse(fetch_task.done())

            fetch_task.cancel()
            await asyncio.sleep(0)

            self.assertFalse(fetch_task.done())
            self.assertEqual(self.manager.active_requests, 1)
            self.assertFalse(self.manager.idle_event.is_set())
        finally:
            self.manager.lock.release()
            fetch_outcome = await asyncio.wait_for(
                asyncio.gather(fetch_task, return_exceptions=True),
                timeout=1.0,
            )
            if self.manager.active_requests > 0:
                await self.manager._release_session(self.manager.generation)

        self.assertIsInstance(fetch_outcome[0], asyncio.CancelledError)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertTrue(self.manager.idle_event.is_set())
        await asyncio.wait_for(self.manager.close(), timeout=1.0)

    async def test_close_prevents_retry_after_blocked_session_loss(self):
        request_started = asyncio.Event()
        release_request = asyncio.Event()

        async def block_session_loss(_payload):
            request_started.set()
            await release_request.wait()
            self.server.existing = False
            return FakeResponse(
                {"status": "error", "message": "The session does not exist"}
            )

        self.server.queue("request.get", block_session_loss)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await request_started.wait()
        close_task = asyncio.create_task(self.manager.close())

        try:
            await asyncio.sleep(0)
            self.assertFalse(close_task.done())
        finally:
            release_request.set()
            fetch_result = await fetch_task
            await close_task

        self.assertIsNone(fetch_result)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertFalse(self.manager.created)
        self.assertEqual(self.server.commands(), ["sessions.create", "request.get"])
        self.assertEqual(self.server.commands().count("sessions.create"), 1)

    async def test_close_cancels_blocked_reaper_destroy_then_destroys_itself(self):
        await self.manager.fetch(PAGE_URL)
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        destroy_started = asyncio.Event()
        destroy_cancelled = asyncio.Event()
        release_destroy = asyncio.Event()

        async def block_destroy(_payload):
            destroy_started.set()
            try:
                await release_destroy.wait()
            except asyncio.CancelledError:
                destroy_cancelled.set()
                raise
            return FakeResponse({"status": "ok"})

        self.server.queue("sessions.destroy", block_destroy)
        reaper_task = asyncio.create_task(
            self.manager._reap_if_idle(),
            name="test-cf-solver-reaper",
        )
        self.manager.reaper_task = reaper_task
        await destroy_started.wait()
        close_task = asyncio.create_task(self.manager.close())

        try:
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertTrue(destroy_cancelled.is_set())
            self.assertTrue(close_task.done())
            await close_task
        finally:
            release_destroy.set()
            await asyncio.gather(reaper_task, close_task, return_exceptions=True)

        self.assertTrue(reaper_task.cancelled())
        self.assertIsNone(self.manager.reaper_task)
        self.assertFalse(self.manager.created)
        self.assertEqual(
            self.server.commands(),
            [
                "sessions.create",
                "request.get",
                "sessions.destroy",
                "sessions.destroy",
            ],
        )

    async def test_external_cancellation_of_close_during_drain_propagates(self):
        request_started = asyncio.Event()
        release_request = asyncio.Event()

        async def block_success(_payload):
            request_started.set()
            await release_request.wait()
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": PAGE_HTML},
                }
            )

        self.server.queue("request.get", block_success)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await request_started.wait()
        close_task = asyncio.create_task(self.manager.close())

        try:
            await asyncio.sleep(0)
            self.assertFalse(close_task.done())
            close_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await close_task
        finally:
            release_request.set()
            fetch_result = await fetch_task
            await asyncio.gather(close_task, return_exceptions=True)

        self.assertEqual(fetch_result, PAGE_HTML)
        self.assertTrue(self.manager.created)
        self.assertNotIn("sessions.destroy", self.server.commands())

    async def test_later_close_intent_wins_after_cancelled_close_and_waiting_start(self):
        request_started = asyncio.Event()
        release_request = asyncio.Event()

        async def block_success(_payload):
            request_started.set()
            await release_request.wait()
            return FakeResponse(
                {
                    "status": "ok",
                    "solution": {"status": 200, "response": PAGE_HTML},
                }
            )

        self.server.queue("request.get", block_success)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await asyncio.wait_for(request_started.wait(), timeout=1.0)

        close_one = asyncio.create_task(self.manager.close())
        await asyncio.sleep(0)
        self.assertFalse(close_one.done())
        close_one.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(close_one, timeout=1.0)

        start_task = asyncio.create_task(self.manager.start())
        await asyncio.sleep(0)
        self.assertTrue(self.manager.lifecycle_lock.locked())
        self.assertFalse(start_task.done())

        close_two = asyncio.create_task(self.manager.close())
        await asyncio.sleep(0)
        self.assertFalse(close_two.done())

        try:
            release_request.set()
            fetch_result, _, _ = await asyncio.wait_for(
                asyncio.gather(fetch_task, start_task, close_two),
                timeout=1.0,
            )
        finally:
            release_request.set()
            for task in (fetch_task, start_task, close_two):
                if not task.done():
                    task.cancel()
            await asyncio.gather(
                fetch_task,
                start_task,
                close_two,
                return_exceptions=True,
            )

        self.assertEqual(fetch_result, PAGE_HTML)
        self.assertTrue(self.manager.closing)
        self.assertFalse(self.manager.created)
        self.assertIsNone(self.manager.reaper_task)

        calls_after_close = list(self.server.calls)
        self.assertIsNone(
            await asyncio.wait_for(
                self.manager.fetch(f"{PAGE_URL}?after-later-close=1"),
                timeout=1.0,
            )
        )
        self.assertEqual(self.server.calls, calls_after_close)
        self.assertEqual(self.server.commands().count("sessions.create"), 1)

    async def test_external_cancellation_while_close_awaits_reaper_propagates(self):
        await self.manager.fetch(PAGE_URL)
        reaper_cancel_seen = asyncio.Event()
        release_reaper = asyncio.Event()

        async def cancellation_delaying_reaper():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                reaper_cancel_seen.set()
                await release_reaper.wait()

        reaper_task = asyncio.create_task(cancellation_delaying_reaper())
        self.manager.reaper_task = reaper_task
        close_task = asyncio.create_task(self.manager.close())
        await reaper_cancel_seen.wait()

        try:
            close_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await close_task
        finally:
            release_reaper.set()
            if not reaper_task.done():
                reaper_task.cancel()
            await asyncio.gather(reaper_task, close_task, return_exceptions=True)

        self.assertTrue(self.manager.created)
        self.assertNotIn("sessions.destroy", self.server.commands())

    async def test_close_during_session_create_destroys_without_acquiring_request(self):
        create_started = asyncio.Event()
        release_create = asyncio.Event()

        async def block_create(_payload):
            create_started.set()
            await release_create.wait()
            return FakeResponse({"status": "ok"})

        self.server.queue("sessions.create", block_create)
        fetch_task = asyncio.create_task(self.manager.fetch(PAGE_URL))
        await create_started.wait()
        close_task = asyncio.create_task(self.manager.close())
        await asyncio.sleep(0)

        release_create.set()
        fetch_result, _ = await asyncio.gather(fetch_task, close_task)

        self.assertIsNone(fetch_result)
        self.assertEqual(self.manager.active_requests, 0)
        self.assertFalse(self.manager.created)
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "sessions.destroy"],
        )
        self.assertNotIn("request.get", self.server.commands())

    async def test_reaps_after_ttl_then_lazily_recreates_with_identical_html(self):
        before_idle = await self.manager.fetch(PAGE_URL)
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)

        await self.manager._reap_if_idle()

        self.assertFalse(self.manager.created)
        self.assertIsNone(self.manager.last_used_at)
        self.assertEqual(self.server.commands().count("sessions.destroy"), 1)

        after_idle = await self.manager.fetch(PAGE_URL)
        self.assertEqual((before_idle, after_idle), (PAGE_HTML, PAGE_HTML))
        self.assertEqual(self.server.commands().count("sessions.create"), 2)

    async def test_failed_idle_destroy_retains_state_and_retries(self):
        await self.manager.fetch(PAGE_URL)
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        self.server.queue(
            "sessions.destroy",
            FakeResponse({"status": "error", "message": "browser busy"}),
            FakeResponse({"status": "ok"}),
        )

        await self.manager._reap_if_idle()
        self.assertTrue(self.manager.created)

        await self.manager._reap_if_idle()
        self.assertFalse(self.manager.created)
        self.assertEqual(self.server.commands().count("sessions.destroy"), 2)

    async def test_http_error_missing_session_clears_idle_state(self):
        await self.manager.fetch(PAGE_URL)
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        self.server.queue(
            "sessions.destroy",
            FakeResponse(
                {"status": "error", "message": "The session does not exist"},
                status_code=500,
            ),
        )

        await self.manager._reap_if_idle()

        self.assertFalse(self.manager.created)
        self.assertIsNone(self.manager.last_used_at)

    async def test_http_error_status_ok_retains_idle_state(self):
        await self.manager.fetch(PAGE_URL)
        last_used_at = self.manager.last_used_at
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        self.server.queue(
            "sessions.destroy",
            FakeResponse({"status": "ok"}, status_code=500),
        )

        await self.manager._reap_if_idle()

        self.assertTrue(self.manager.created)
        self.assertEqual(self.manager.last_used_at, last_used_at)

    async def test_malformed_idle_destroy_response_is_safe_and_retains_state(self):
        await self.manager.fetch(PAGE_URL)
        last_used_at = self.manager.last_used_at
        self.clock.advance(cf_solver._IDLE_TTL_SECONDS)
        self.server.queue("sessions.destroy", MalformedResponse(status_code=500))

        await self.manager._reap_if_idle()

        self.assertTrue(self.manager.created)
        self.assertEqual(self.manager.last_used_at, last_used_at)

    async def test_lost_session_rebuilds_once_and_retries_request_once(self):
        self.server.queue(
            "request.get",
            FakeResponse({"status": "error", "message": "Session not found"}),
        )

        result = await self.manager.fetch(PAGE_URL)

        self.assertEqual(result, PAGE_HTML)
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "request.get", "sessions.create", "request.get"],
        )
        request_calls = [
            call["json"] for call in self.server.calls if call["json"]["cmd"] == "request.get"
        ]
        self.assertEqual(len(request_calls), 2)
        self.assertTrue(all(call["session"] == cf_solver._SESSION_ID for call in request_calls))

    async def test_two_lost_session_responses_stop_after_second_request(self):
        self.server.queue(
            "request.get",
            FakeResponse({"status": "error", "message": "Session not found"}),
            FakeResponse({"status": "error", "message": "Session not found"}),
        )

        result = await self.manager.fetch(PAGE_URL)

        self.assertIsNone(result)
        self.assertEqual(
            self.server.commands(),
            ["sessions.create", "request.get", "sessions.create", "request.get"],
        )
        self.assertEqual(self.server.commands().count("request.get"), 2)
        self.assertFalse(self.manager.created)
        self.assertIsNone(self.manager.last_used_at)

    async def test_close_cancels_and_awaits_reaper_then_destroys_session(self):
        self.server.existing = True
        await self.manager.start()
        reaper_task = self.manager.reaper_task

        await self.manager.close()

        self.assertTrue(reaper_task.done())
        self.assertTrue(reaper_task.cancelled())
        self.assertIsNone(self.manager.reaper_task)
        self.assertFalse(self.manager.created)
        self.assertEqual(self.server.commands(), ["sessions.list", "sessions.destroy"])

    async def test_close_failed_destroy_returns_and_retains_retryable_state(self):
        self.server.existing = True
        await self.manager.start()
        last_used_at = self.manager.last_used_at
        self.server.queue(
            "sessions.destroy",
            FakeResponse(
                {"status": "error", "message": "browser busy"},
                status_code=500,
            ),
        )

        await self.manager.close()

        self.assertIsNone(self.manager.reaper_task)
        self.assertTrue(self.manager.created)
        self.assertEqual(self.manager.last_used_at, last_used_at)
        self.assertEqual(self.server.commands(), ["sessions.list", "sessions.destroy"])

    async def test_public_fetch_failure_paths_return_none(self):
        async def raise_request(_payload):
            raise RuntimeError("request transport failed")

        failures = (
            (
                "http non-200",
                FakeResponse(
                    {"status": "error", "message": "gateway unavailable"},
                    status_code=503,
                ),
            ),
            (
                "ordinary status non-ok",
                FakeResponse({"status": "error", "message": "solver overloaded"}),
            ),
            (
                "upstream non-200",
                FakeResponse(
                    {
                        "status": "ok",
                        "solution": {"status": 503, "response": "bad gateway"},
                    }
                ),
            ),
            ("malformed JSON", MalformedResponse()),
            ("request exception", raise_request),
        )

        with patch.object(cf_solver, "_session_manager", self.manager):
            for label, response in failures:
                with self.subTest(label=label):
                    self.server.queue("request.get", response)
                    result = await cf_solver.fetch_with_cf_solver(PAGE_URL)
                    self.assertIsNone(result)

        self.assertEqual(self.server.commands().count("request.get"), len(failures))
        self.assertEqual(self.manager.active_requests, 0)

    async def test_public_start_prepares_browser_without_visiting_protected_sites(self):
        self.server.queue("sessions.create", FakeResponse({"status": "ok"}))
        with patch.object(cf_solver, "_session_manager", self.manager), patch.object(
            cf_solver, "_warmup_task", None
        ):
            await cf_solver.start_session_manager()
            await asyncio.sleep(0)

            self.assertEqual(
                self.server.commands()[:2],
                ["sessions.list", "sessions.create"],
            )
            self.assertNotIn("request.get", self.server.commands())

            await cf_solver.close_session_manager()

    async def test_keepalive_interval_is_shorter_than_idle_ttl(self):
        self.assertLess(
            cf_solver._KEEPALIVE_INTERVAL_SECONDS,
            cf_solver._IDLE_TTL_SECONDS,
        )
        self.assertGreaterEqual(cf_solver._KEEPALIVE_INTERVAL_SECONDS, 15 * 60)
        self.assertGreaterEqual(cf_solver._INITIAL_WARMUP_DELAY_SECONDS, 60)
        self.assertEqual(cf_solver._WARMUP_TARGETS, ("https://jable.tv/",))
        self.assertIn("https://missav.ai/", cf_solver._KEEPALIVE_TARGETS)

    async def test_production_session_serializes_browser_requests(self):
        manager = cf_solver._SessionManager(
            monotonic=self.clock,
            serialize_requests=True,
        )
        first_started = asyncio.Event()
        release_first = asyncio.Event()

        async def block_first(_payload):
            first_started.set()
            await release_first.wait()
            return FakeResponse({
                "status": "ok",
                "solution": {"status": 200, "response": "first"},
            })

        self.server.queue(
            "sessions.create",
            FakeResponse({"status": "ok"}),
        )
        self.server.queue(
            "request.get",
            block_first,
            FakeResponse({
                "status": "ok",
                "solution": {"status": 200, "response": "second"},
            }),
        )

        first = asyncio.create_task(manager.fetch(PAGE_URL + "?first=1"))
        await first_started.wait()
        second = asyncio.create_task(manager.fetch(PAGE_URL + "?second=1"))
        await asyncio.sleep(0)

        self.assertEqual(self.server.commands().count("request.get"), 1)
        self.assertEqual(manager.active_requests, 2)

        release_first.set()
        self.assertEqual(await asyncio.gather(first, second), ["first", "second"])
        self.assertEqual(self.server.commands().count("request.get"), 2)

    async def test_unconfigured_solver_makes_no_network_calls(self):
        with patch.object(
            cf_solver,
            "Config",
            return_value=SimpleNamespace(stream_cf_solver_url="  "),
        ), patch.object(cf_solver, "_session_manager", self.manager):
            await cf_solver.start_session_manager()
            result = await cf_solver.fetch_with_cf_solver(PAGE_URL)
            await cf_solver.close_session_manager()

        self.assertIsNone(result)
        self.assertEqual(self.server.calls, [])
        self.assertIsNone(self.manager.reaper_task)


if __name__ == "__main__":
    unittest.main()
