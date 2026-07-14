# Cross-Loop HTTP Client Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give InfoClient and Open115 exactly one owned HTTP transport per event loop, cancellation-safe process-wide coordination, and bounded owner-loop shutdown.

**Architecture:** A reusable `LoopClientPool` leases loop-affine clients, rejects acquisitions after shutdown begins, drains active leases, and retains timed-out close attempts without double-closing. InfoClient and the owned Open115 path use this pool. Open115 throttling reserves global time slots under a short thread lock, while token refresh uses a cross-loop concurrent-future single-flight.

**Tech Stack:** Python 3, asyncio, `concurrent.futures`, threading, httpx, pytest/unittest, FastAPI shutdown hooks.

---

## Execution Constraints

- The implementation depends on the current uncommitted project state. Do not create a clean worktree from `HEAD` unless it first receives the current tracked and untracked baseline.
- The commit blocks below define logical boundaries. In the current dirty checkout, never broadly stage `backend/scheduler/tasks.py`, `backend/test_main_app_boundary.py`, or any other pre-dirty path; isolate exact new hunks or leave the checkpoint uncommitted.
- Keep `backend/scheduler/worker_loop.py` running until client shutdown finishes; no worker-loop stop change is required.
- Do not require live 115 credentials in CI. The synthetic request-loop/worker-loop regression is mandatory; live 115 verification is conditional on an existing valid binding.
- Fixed time bounds: pool lease drain `5.0s`, each client close observation `5.0s`, and all manual scheduler-thread joins share one `10.0s` deadline.

## File Map

- Create `backend/modules/loop_client_pool.py`: loop-owned lease pool and bounded close state machine.
- Create `backend/test_loop_client_pool.py`: two persistent-loop ownership, drain, close, timeout, retry, and cancellation tests.
- Modify `backend/modules/info_client.py:208-235,236-386,932-994`: pool construction, leases, and shutdown.
- Create `backend/test_info_client_loop_ownership.py`: A-B-A reuse and owner-loop close.
- Modify `backend/test_info_client_errors.py`, `backend/test_categories_route.py`, and `backend/test_security_hardening.py`: factory-based test injection.
- Modify `backend/services/open115.py:125-198,342-363`: owned transport pool, global slot reservation, and refresh single-flight.
- Modify `backend/test_open115.py`: owned/injected transport, throttle, and refresh cancellation regressions.
- Modify `backend/test_open115_downloader.py`: submit-on-request-loop/poll-on-worker-loop workflow.
- Modify `backend/scheduler/tasks.py:309-334,383-385`: bounded manual-job drain before client close.
- Modify `backend/test_scheduler_run.py`: shared-deadline drain tests.
- Modify `backend/test_main_app_boundary.py`: lock in scheduler-before-client shutdown ordering; no `backend/main.py` production change is planned.

### Task 1: Build the Loop-Owned Lease Pool

**Files:**
- Create: `backend/modules/loop_client_pool.py`
- Create: `backend/test_loop_client_pool.py`

- [ ] **Step 1: Write the persistent-loop A-B-A and concurrent-first-lease tests**

Create a test-only `LoopThread` that starts `asyncio.new_event_loop()` in a named thread, exposes `run(coro)` via `asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=2)`, and stops/joins/closes the loop in cleanup. Use a fake client that records its creation loop, close loop, `is_closed`, and close count.

```python
class RecordingClient:
    def __init__(self):
        self.created_loop = asyncio.get_running_loop()
        self.closed_loop = None
        self.close_count = 0
        self.is_closed = False

    async def aclose(self) -> None:
        self.close_count += 1
        self.closed_loop = asyncio.get_running_loop()
        self.is_closed = True


async def leased_identity(pool):
    async with pool.lease() as client:
        return id(client)
```

Assert A-B-A yields two factory calls and identities `A1, B1, A1`. On one loop, `asyncio.gather()` 20 simultaneous first leases must yield one identity and one factory call.

Add two small lifecycle cases: a factory exception must leave no cached entry and allow the next lease to create normally; an externally closed client must be replaced only in its own loop.

- [ ] **Step 2: Write failing close lifecycle tests**

Cover all of these with deterministic events and short constructor timeouts:

- an active lease delays close; after close starts, a new lease raises `PoolClosedError`;
- clients created on loop A and B run `aclose()` on A and B when `close_all()` is called from a third loop;
- one client whose first `aclose()` raises remains retained, does not block another client closing, and closes on the next `close_all()`;
- a stopped owner loop returns within the close timeout and retains its client;
- an `aclose()` that ignores initial cancellation is represented by one retained close attempt, never two concurrent calls;
- canceling the first `close_all()` waiter does not cancel the internal close leader; releasing the lease still closes the client.

- [ ] **Step 3: Run the pool test and confirm the module is absent**

Run: `.venv/bin/python -m pytest backend/test_loop_client_pool.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'modules.loop_client_pool'`.

- [ ] **Step 4: Implement the pool interface and lease accounting**

The module starts with these types and state:

```python
from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator, Callable
from concurrent.futures import Future
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import Generic, Protocol, TypeVar

logger = logging.getLogger(__name__)


class AsyncClosable(Protocol):
    @property
    def is_closed(self) -> bool:
        raise NotImplementedError

    async def aclose(self) -> None:
        raise NotImplementedError


ClientT = TypeVar("ClientT", bound=AsyncClosable)


@dataclass
class _CloseAttempt:
    outcome: Future[None] = field(default_factory=Future)
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    task: asyncio.Task[None] | None = None


class PoolClosedError(RuntimeError):
    pass


class _PoolState(Enum):
    OPEN = auto()
    CLOSING = auto()
    CLOSED = auto()
```

`LoopClientPool.__init__` must initialize a regular loop-to-client dictionary, short `threading.Lock`, active count, initially-set idle `threading.Event`, state, one shared close future, one internal leader task, and owner-loop close-attempt map:

```python
class LoopClientPool(Generic[ClientT]):
    def __init__(
        self,
        factory: Callable[[], ClientT],
        *,
        drain_timeout: float = 5.0,
        close_timeout: float = 5.0,
    ) -> None:
        self._factory = factory
        self._drain_timeout = max(0.0, float(drain_timeout))
        self._close_timeout = max(0.0, float(close_timeout))
        self._clients: dict[asyncio.AbstractEventLoop, ClientT] = {}
        self._lock = threading.Lock()
        self._active_leases = 0
        self._idle = threading.Event()
        self._idle.set()
        self._state = _PoolState.OPEN
        self._close_future: Future[None] | None = None
        self._close_leader_task: asyncio.Task[None] | None = None
        self._close_attempts: dict[asyncio.AbstractEventLoop, _CloseAttempt] = {}

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[ClientT]:
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._state is not _PoolState.OPEN:
                raise PoolClosedError("HTTP client pool is closing")
            client = self._clients.get(loop)
            if client is None or client.is_closed:
                client = self._factory()
                self._clients[loop] = client
            self._active_leases += 1
            self._idle.clear()
        try:
            yield client
        finally:
            with self._lock:
                self._active_leases -= 1
                if self._active_leases == 0:
                    self._idle.set()
```

- [ ] **Step 5: Implement close single-flight and retained attempts**

`close_all()` must create an internal leader task so caller cancellation only cancels that caller's shielded wait:

```python
    async def close_all(self) -> None:
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._state is _PoolState.CLOSED:
                return
            shared = self._close_future
            start_leader = shared is None
            if shared is None:
                self._state = _PoolState.CLOSING
                shared = Future()
                self._close_future = shared

        if start_leader:
            try:
                leader = loop.create_task(self._run_close_attempt(shared))
            except BaseException as exc:
                with self._lock:
                    if self._close_future is shared:
                        self._close_future = None
                shared.set_exception(exc)
                raise
            with self._lock:
                self._close_leader_task = leader

        waiter = asyncio.wrap_future(shared)
        waiter.add_done_callback(self._consume_waiter)
        await asyncio.shield(waiter)
```

The leader and per-client close methods are:

```python
    async def _run_close_attempt(self, shared: Future[None]) -> None:
        current_task = asyncio.current_task()
        try:
            drained = await asyncio.to_thread(self._idle.wait, self._drain_timeout)
            if not drained:
                logger.warning("HTTP client leases did not drain before shutdown timeout")
            with self._lock:
                clients = tuple(self._clients.items())
            for owner_loop, client in clients:
                try:
                    await self._observe_client_close(owner_loop, client)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Unable to schedule HTTP client close for loop %r", owner_loop)
            with self._lock:
                if not self._clients:
                    self._state = _PoolState.CLOSED
        except BaseException as exc:
            if not shared.done():
                shared.set_exception(exc)
        else:
            if not shared.done():
                shared.set_result(None)
        finally:
            with self._lock:
                if self._close_future is shared:
                    self._close_future = None
                if self._close_leader_task is current_task:
                    self._close_leader_task = None

    @staticmethod
    def _consume_waiter(waiter: asyncio.Future[None]) -> None:
        try:
            waiter.result()
        except BaseException:
            pass

    async def _observe_client_close(
        self,
        owner_loop: asyncio.AbstractEventLoop,
        client: ClientT,
    ) -> None:
        with self._lock:
            if self._clients.get(owner_loop) is not client:
                return
            if client.is_closed:
                del self._clients[owner_loop]
                if not self._clients:
                    self._state = _PoolState.CLOSED
                return
            attempt = self._close_attempts.get(owner_loop)

        if attempt is None:
            if owner_loop.is_closed() or not owner_loop.is_running():
                logger.warning("HTTP client owner loop is unavailable: %r", owner_loop)
                return
            attempt = _CloseAttempt()
            with self._lock:
                self._close_attempts[owner_loop] = attempt
            try:
                owner_loop.call_soon_threadsafe(
                    self._start_client_close,
                    owner_loop,
                    client,
                    attempt,
                )
            except BaseException:
                with self._lock:
                    if self._close_attempts.get(owner_loop) is attempt:
                        del self._close_attempts[owner_loop]
                raise
            attempt.outcome.add_done_callback(partial(self._finish_client_close, owner_loop, client, attempt))

        waiter = asyncio.wrap_future(attempt.outcome)
        waiter.add_done_callback(self._consume_waiter)
        done, _pending = await asyncio.wait(
            {waiter},
            timeout=self._close_timeout,
        )
        if not done:
            attempt.cancel_requested.set()
            owner_loop.call_soon_threadsafe(self._cancel_client_close, attempt)
            logger.warning("Timed out closing HTTP client on loop %r", owner_loop)

    @staticmethod
    def _start_client_close(
        owner_loop: asyncio.AbstractEventLoop,
        client: ClientT,
        attempt: _CloseAttempt,
    ) -> None:
        try:
            task = owner_loop.create_task(client.aclose())
        except BaseException as exc:
            attempt.outcome.set_exception(exc)
            return
        attempt.task = task
        task.add_done_callback(partial(LoopClientPool._report_client_close, attempt))
        if attempt.cancel_requested.is_set():
            task.cancel()

    @staticmethod
    def _cancel_client_close(attempt: _CloseAttempt) -> None:
        if attempt.task is not None and not attempt.task.done():
            attempt.task.cancel()

    @staticmethod
    def _report_client_close(attempt: _CloseAttempt, task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            if not attempt.outcome.done():
                attempt.outcome.cancel()
        except BaseException as exc:
            if not attempt.outcome.done():
                attempt.outcome.set_exception(exc)
        else:
            if not attempt.outcome.done():
                attempt.outcome.set_result(None)

    def _finish_client_close(
        self,
        owner_loop: asyncio.AbstractEventLoop,
        client: ClientT,
        attempt: _CloseAttempt,
        outcome: Future[None],
    ) -> None:
        succeeded = False
        try:
            outcome.result()
        except BaseException as exc:
            logger.warning("HTTP client close failed on loop %r: %s", owner_loop, exc)
        else:
            succeeded = True
        with self._lock:
            if self._close_attempts.get(owner_loop) is attempt:
                del self._close_attempts[owner_loop]
            if (succeeded or client.is_closed) and self._clients.get(owner_loop) is client:
                del self._clients[owner_loop]
            if not self._clients:
                self._state = _PoolState.CLOSED
```

The thread-safe callback creates the real task only on its owner loop. Canceling a timed-out observation requests cancellation of that task but does not mark `outcome` complete; if `aclose()` suppresses cancellation, the attempt remains owned until the task actually finishes. Store the attempt before scheduling owner-loop work and attach the completion callback before any await.

- [ ] **Step 6: Run all pool tests**

Run: `.venv/bin/python -m pytest backend/test_loop_client_pool.py -q`

Expected: all pool tests PASS in under the test suite's bounded timeouts, with no pending-task warnings.

- [ ] **Step 7: Commit the shared pool**

```bash
git add backend/modules/loop_client_pool.py backend/test_loop_client_pool.py
git diff --cached --check
git commit -m "feat: add loop-owned async client pool"
```

### Task 2: Migrate InfoClient and Its Test Doubles to Leases

**Files:**
- Modify: `backend/modules/info_client.py:208-386,932-994`
- Create: `backend/test_info_client_loop_ownership.py`
- Modify: `backend/test_info_client_errors.py:11-41`
- Modify: `backend/test_categories_route.py:73-121`
- Modify: `backend/test_security_hardening.py:194-210`

- [ ] **Step 1: Add a failing A-B-A ownership test**

Use two persistent `LoopThread` instances and a factory whose clients record creation and close loops. Call `InfoClient.get_stats()` on A, B, then A. Assert two clients were created, A's client handled both A calls, and `await client.close()` from the test loop closes both on their recorded owner loops.

The constructor used by the test is:

```python
client = InfoClient(
    api_url="http://javinfo.test",
    client_factory=lambda: RecordingInfoHTTPClient(),
)
```

- [ ] **Step 2: Run the ownership test and confirm constructor failure**

Run: `.venv/bin/python -m pytest backend/test_info_client_loop_ownership.py -q`

Expected: FAIL because `InfoClient.__init__` does not accept `client_factory` and still owns only one overwritten client.

- [ ] **Step 3: Construct the pool lazily and remove `_get_client()`**

```python
from collections.abc import Callable

from modules.loop_client_pool import LoopClientPool


class InfoClient:
    def __init__(
        self,
        api_url: str = "http://localhost:18080",
        timeout: int = 30,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        factory = client_factory or self._new_client
        self._client_pool = LoopClientPool(factory)

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, trust_env=False)

    async def close(self) -> None:
        await self._client_pool.close_all()
```

- [ ] **Step 4: Hold a lease around every complete request**

Replace all ten `_get_client()` call sites. `_get`, `_get_list`, `proxy_get`, `proxy_post`, `proxy_post_long`, and `proxy_patch` use this exact structure:

```python
        async with self._client_pool.lease() as client:
            try:
                response = await client.get(f"{self.api_url}{path}", params=params)
            except httpx.RequestError as exc:
                raise _map_request_error(path, exc) from exc
```

`_get_all_pages.fetch_page()` acquires its own lease so concurrent page requests increment/decrement independently. Each of `batch_get_videos`, `batch_lookup_by_dvd_id`, and `batch_get_actress_videos` holds one lease around its whole batching loop. Keep decoding, URL, parameters, auth headers, timeout, transformation, and error mapping byte-for-byte equivalent.

- [ ] **Step 5: Migrate the four old `_get_client` mocks**

Give every fake `is_closed = False` and an async `aclose()` method. Instantiate `InfoClient(client_factory=lambda: fake_http)` in `test_info_client_errors.py`, both relevant category tests, and the PATCH auth test. Remove all patches of the deleted `_get_client` method.

- [ ] **Step 6: Run InfoClient ownership and compatibility tests**

Run: `.venv/bin/python -m pytest backend/test_info_client_loop_ownership.py backend/test_info_client_errors.py backend/test_categories_route.py backend/test_security_hardening.py backend/test_info_client_video_detail.py backend/test_subscription_scope.py -q`

Expected: all tests PASS; the ownership test records exactly two clients and both owner-loop closes.

- [ ] **Step 7: Commit InfoClient integration**

```bash
git add backend/modules/info_client.py backend/test_info_client_loop_ownership.py backend/test_info_client_errors.py backend/test_categories_route.py backend/test_security_hardening.py
git diff --cached --check
git commit -m "fix: retain JavInfo clients per event loop"
```

### Task 3: Isolate Open115 Transports and Reserve Global Request Slots

**Files:**
- Modify: `backend/services/open115.py:9-22,125-198`
- Modify: `backend/test_open115.py`

- [ ] **Step 1: Add failing owned/injected and cross-loop throttle tests**

Add an optional `http_client_factory` test that creates a recording client on each of two persistent loops. Make one `_request()` call on A, one on B, then one on A; assert two owned clients and A1/B1/A1 reuse. After `close()`, assert owner-loop closes.

Retain an injected `SequenceHTTPClient`, call `close()`, and assert its `aclose()` was not called.

For throttling, start one request on each loop at a barrier using a loop-agnostic injected fake. Record monotonic request times and require adjacent starts to be at least the configured interval minus a small scheduler tolerance.

- [ ] **Step 2: Run the new Open115 tests against the singleton transport**

Run: `.venv/bin/python -m pytest backend/test_open115.py -q`

Expected: FAIL because `http_client_factory` is unsupported, the owned transport is global, and the throttle lock is loop-bound.

- [ ] **Step 3: Add mutually exclusive injected and owned transport paths**

```python
from collections.abc import Callable
from concurrent.futures import Future

from modules.loop_client_pool import LoopClientPool


class Open115Client:
    def __init__(
        self,
        *,
        config_obj: Any = config,
        http_client: Any | None = None,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
        min_request_interval: float = MIN_REQUEST_INTERVAL,
    ) -> None:
        if http_client is not None and http_client_factory is not None:
            raise ValueError("http_client and http_client_factory are mutually exclusive")
        self._config = config_obj
        self._http = http_client
        self._http_pool = None if http_client is not None else LoopClientPool(
            http_client_factory or self._new_http_client
        )
        self._min_request_interval = max(0.0, float(min_request_interval))
        self._throttle_lock = threading.Lock()
        self._next_request_at = 0.0
        self._refresh_state_lock = threading.Lock()
        self._refresh_inflight: Future[bool] | None = None
        self._persist_lock = threading.Lock()
        self._pending_auth = {}
        self._folder_cache = {"/": "0"}

    @staticmethod
    def _new_http_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(OPEN115_TIMEOUT),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._http_pool is not None:
            await self._http_pool.close_all()
```

- [ ] **Step 4: Replace throttle locking with nonblocking slot reservation**

```python
    async def _wait_for_request_slot(self) -> None:
        with self._throttle_lock:
            now = time.monotonic()
            slot = max(now, self._next_request_at)
            self._next_request_at = slot + self._min_request_interval
        delay = slot - now
        if delay > 0:
            await asyncio.sleep(delay)
```

Call it at the start of `_request()`. Then request through the injected object directly or hold an owned pool lease for the complete request. Keep existing `httpx.RequestError -> Open115Error` mapping unchanged.

```python
    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        await self._wait_for_request_slot()
        try:
            if self._http_pool is not None:
                async with self._http_pool.lease() as http_client:
                    return await http_client.request(method, url, **kwargs)
            return await self._http.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise Open115Error(None, "115 Open API 连接失败") from exc
```

- [ ] **Step 5: Run Open115 transport tests**

Run: `.venv/bin/python -m pytest backend/test_open115.py backend/test_open115_files_route.py backend/test_movie_resources_routes.py -q`

Expected: all tests PASS; injected ownership behavior remains unchanged.

- [ ] **Step 6: Commit transport isolation**

```bash
git add backend/services/open115.py backend/test_open115.py
git diff --cached --check
git commit -m "fix: isolate Open115 transports by event loop"
```

### Task 4: Replace the Refresh Lock With Cross-Loop Single-Flight

**Files:**
- Modify: `backend/services/open115.py:342-363`
- Modify: `backend/test_open115.py:108-136`

- [ ] **Step 1: Add failing cross-loop and cancellation tests**

Cover these exact cases with two persistent loops and a blocking refresh fake:

- 64 concurrent followers across A/B join one leader and produce one refresh HTTP call;
- while followers wait, `asyncio.to_thread(lambda: 42)` completes, proving no follower consumes an executor thread;
- cancel one follower, release the leader, and assert other followers succeed and the next refresh does not deadlock;
- cancel the leader, assert that batch's followers receive cancellation, then call refresh again and assert a new leader succeeds.

- [ ] **Step 2: Run the cancellation tests against `asyncio.Lock`**

Run: `.venv/bin/python -m pytest backend/test_open115.py -q`

Expected: cross-loop refresh raises loop-affinity errors or the cancellation test times out.

- [ ] **Step 3: Extract one leader refresh operation**

Move the current body into this exact leader operation:

```python
    async def _refresh_access_token_once(
        self,
        expected_access_token: str | None,
    ) -> bool:
        if (
            expected_access_token is not None
            and self.access_token
            and self.access_token != expected_access_token
        ):
            return True
        refresh_token = self.refresh_token
        if not refresh_token:
            return False
        try:
            tokens = await self._passport_request(
                "POST",
                f"{PASSPORT_BASE}/open/refreshToken",
                data={"refresh_token": refresh_token},
            )
            self._persist_tokens(tokens)
        except Open115Error:
            logger.warning("115 Open token refresh failed")
            return False
        return bool(self.access_token)
```

- [ ] **Step 4: Implement concurrent-future single-flight**

```python
    async def refresh_access_token(self, *, expected_access_token: str | None = None) -> bool:
        with self._refresh_state_lock:
            if (
                expected_access_token is not None
                and self.access_token
                and self.access_token != expected_access_token
            ):
                return True
            shared = self._refresh_inflight
            leader = shared is None
            if shared is None:
                shared = Future()
                self._refresh_inflight = shared

        if not leader:
            waiter = asyncio.wrap_future(shared)
            waiter.add_done_callback(self._consume_refresh_waiter)
            return await asyncio.shield(waiter)

        try:
            result = await self._refresh_access_token_once(expected_access_token)
        except asyncio.CancelledError:
            shared.cancel()
            raise
        except BaseException as exc:
            shared.set_exception(exc)
            raise
        else:
            shared.set_result(result)
            return result
        finally:
            with self._refresh_state_lock:
                if self._refresh_inflight is shared:
                    self._refresh_inflight = None

    @staticmethod
    def _consume_refresh_waiter(waiter: asyncio.Future[bool]) -> None:
        try:
            waiter.result()
        except BaseException:
            pass
```

The leader's existing `Open115Error` path remains inside `_refresh_access_token_once()` and returns `False`; unknown exceptions still propagate to every follower.

- [ ] **Step 5: Run all Open115 tests**

Run: `.venv/bin/python -m pytest backend/test_open115.py backend/test_open115_routes.py backend/test_open115_files_route.py -q`

Expected: all tests PASS, one refresh call per batch, and no timeout/deadlock.

- [ ] **Step 6: Commit refresh coordination**

```bash
git add backend/services/open115.py backend/test_open115.py
git diff --cached --check
git commit -m "fix: coordinate Open115 token refresh across loops"
```

### Task 5: Prove Submit/Poll Cross-Loop Progression

**Files:**
- Modify: `backend/test_open115_downloader.py`

- [ ] **Step 1: Add the end-to-end synthetic loop-affinity regression**

Create an owned `Open115Client` whose factory returns one fake per running loop. The fake returns an accepted hash for `/open/offline/add_task_urls` and a completed task for `/open/offline/get_task_list`. Keep a persistent request-loop thread alive, submit `client.add_offline_task()` there, create the matching DB download row, then run `downloader_service.poll_task_status(task_id)` through `scheduler.worker_loop.run()` with finalization mocked.

Assert:

- two HTTP clients were created on two different loops;
- no loop-affinity exception was logged or returned;
- the DB task reaches `completed` with the result folder id;
- finalization receives the expected task/movie/folder IDs;
- `client.close()` closes both transports before the request loop is stopped.

- [ ] **Step 2: Run the regression**

Run: `.venv/bin/python -m pytest backend/test_open115_downloader.py backend/test_acquisition_coordinator.py -q`

Expected: PASS with the pooled implementation. Reverting the pool integration must reproduce a loop-affinity failure or leave the task nonterminal.

- [ ] **Step 3: Commit the workflow regression**

```bash
git add backend/test_open115_downloader.py
git diff --cached --check
git commit -m "test: cover cross-loop Open115 task polling"
```

### Task 6: Drain Manual Scheduler Jobs Before Client Shutdown

**Files:**
- Modify: `backend/scheduler/tasks.py:309-334,383-385`
- Modify: `backend/test_scheduler_run.py`
- Modify: `backend/test_main_app_boundary.py`

- [ ] **Step 1: Add failing shared-deadline manual-thread tests**

Register two blocking threads in `_manual_run_threads`. Call `drain_manual_scheduler_jobs(timeout=0.2)` and assert total elapsed time is bounded near `0.2s`, not `0.4s`, and both live thread names are returned/logged. Add a second test that releases both threads and asserts the returned tuple is empty.

- [ ] **Step 2: Implement one shared deadline and call it from shutdown**

```python
MANUAL_JOB_SHUTDOWN_TIMEOUT = 10.0


def drain_manual_scheduler_jobs(timeout: float = MANUAL_JOB_SHUTDOWN_TIMEOUT) -> tuple[str, ...]:
    deadline = time.monotonic() + max(0.0, float(timeout))
    with _manual_run_lock:
        threads = tuple(thread for thread in _manual_run_threads.values() if thread.is_alive())
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
    alive = tuple(thread.name for thread in threads if thread.is_alive())
    for name in alive:
        logger.warning("Manual scheduler job thread still running during shutdown: %s", name)
    return alive


def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
    finally:
        drain_manual_scheduler_jobs()
```

- [ ] **Step 3: Lock in main shutdown ordering without changing `main.py`**

Add a `shutdown_event` test that records calls from patched `scheduler.tasks.stop_scheduler`, `get_info_client().close`, and `open115_client.close`. Assert the scheduler stop occurs first, InfoClient closes second, and Open115 closes third. Patch sing-box and playback close so the test has no external effects.

- [ ] **Step 4: Run scheduler and shutdown tests**

Run: `.venv/bin/python -m pytest backend/test_scheduler_run.py backend/test_scheduler_status.py backend/test_main_app_boundary.py backend/test_trace_propagation.py backend/test_job_model.py -q`

Expected: all tests PASS; bounded drain warnings appear only in the explicit timeout test.

- [ ] **Step 5: Commit scheduler quiescence**

```bash
git add backend/scheduler/tasks.py backend/test_scheduler_run.py backend/test_main_app_boundary.py
git diff --cached --check
git commit -m "fix: drain manual scheduler jobs before client shutdown"
```

### Task 7: Full and Runtime Verification

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Run the complete focused matrix**

Run: `.venv/bin/python -m pytest backend/test_loop_client_pool.py backend/test_info_client_loop_ownership.py backend/test_info_client_errors.py backend/test_categories_route.py backend/test_security_hardening.py backend/test_open115.py backend/test_open115_routes.py backend/test_open115_files_route.py backend/test_open115_downloader.py backend/test_acquisition_coordinator.py backend/test_scheduler_run.py backend/test_scheduler_status.py backend/test_main_app_boundary.py -q`

Expected: zero failures, no pending-task warnings, and no loop-affinity exceptions.

- [ ] **Step 2: Run the complete backend suite and dependency check**

Run: `.venv/bin/python -m pytest backend -q`

Expected: zero failures.

Run: `.venv/bin/python -m pip check`

Expected: `No broken requirements found.`

- [ ] **Step 3: Check source hygiene**

Run: `git diff --check`

Expected: exit 0.

- [ ] **Step 4: Restart only the backend through the service helper**

Run: `scripts/services.sh restart backend`

Expected: graceful shutdown completes without pending-client warnings.

Run: `scripts/services.sh status`

Expected: backend port `18090` is healthy; JavInfo and frontend remain healthy.

- [ ] **Step 5: Inspect logs for the original failure**

Run: `scripts/services.sh logs backend --no-follow | tail -n 500 | rg "different event loop|Event loop is closed|pending.*task|AsyncClient"`

Expected: no new shutdown or loop-affinity errors after the restart and synthetic submit/poll test.

- [ ] **Step 6: Perform conditional live verification**

When the configured 115 binding is valid, submit one harmless test task through the existing API, allow the scheduled coordinator to poll it, and require terminal progression without `is bound to a different event loop`. When credentials are unavailable, record the synthetic two-loop regression as the deterministic evidence and do not weaken CI.

- [ ] **Step 7: Compare resource ownership across repeated loop alternation**

Record the backend PID and its open socket/file count, run the deterministic request-loop/worker-loop alternation 100 times, then record the count again. Require the count to stabilize after the two per-loop pools are created rather than increasing once per handoff. Use `scripts/services.sh status` to identify service state and read-only `lsof -p <pid>` for counts.

- [ ] **Step 8: Review final integration scope**

Run: `git status --short`

Run: `git log -6 --oneline`

Expected: the six planned commits are present and no unrelated files were staged or committed.
