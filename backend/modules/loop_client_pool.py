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
    def is_closed(self) -> bool: ...

    async def aclose(self) -> None: ...


ClientT = TypeVar("ClientT", bound=AsyncClosable)


class PoolClosedError(RuntimeError):
    pass


class _PoolState(Enum):
    OPEN = auto()
    CLOSING = auto()
    CLOSED = auto()


@dataclass
class _CloseAttempt:
    outcome: Future[None] = field(default_factory=Future)
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    task: asyncio.Task[None] | None = None


class LoopClientPool(Generic[ClientT]):
    """Retain one async client per event loop and close it on its owner loop."""

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
        self._failed_close_loops: set[asyncio.AbstractEventLoop] = set()

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
                self._failed_close_loops.discard(loop)
            self._active_leases += 1
            self._idle.clear()
        try:
            yield client
        finally:
            with self._lock:
                self._active_leases -= 1
                if self._active_leases == 0:
                    self._idle.set()

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

    async def _run_close_attempt(self, shared: Future[None]) -> None:
        current_task = asyncio.current_task()
        try:
            drained = await self._wait_for_idle()
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

    async def _wait_for_idle(self) -> bool:
        if self._idle.is_set():
            return True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._drain_timeout
        while not self._idle.is_set():
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(0.01, remaining))
        return True

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
            retry_required = owner_loop in self._failed_close_loops
            if client.is_closed and not retry_required:
                del self._clients[owner_loop]
                self._failed_close_loops.discard(owner_loop)
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
            attempt.outcome.add_done_callback(
                partial(self._finish_client_close, owner_loop, client, attempt)
            )

        waiter = asyncio.wrap_future(attempt.outcome)
        waiter.add_done_callback(self._consume_waiter)
        done, _pending = await asyncio.wait({waiter}, timeout=self._close_timeout)
        if not done:
            attempt.cancel_requested.set()
            if owner_loop.is_running() and not owner_loop.is_closed():
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
            if self._clients.get(owner_loop) is client:
                if succeeded:
                    del self._clients[owner_loop]
                    self._failed_close_loops.discard(owner_loop)
                else:
                    self._failed_close_loops.add(owner_loop)
            if not self._clients:
                self._state = _PoolState.CLOSED
