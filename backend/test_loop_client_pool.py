from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

import pytest

from modules.loop_client_pool import LoopClientPool, PoolClosedError


class LoopThread:
    def __init__(self, name: str):
        self.loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self.thread = threading.Thread(target=self._run, name=name, daemon=True)
        self.thread.start()
        assert self._ready.wait(2)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def submit(self, coroutine) -> Future:
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def run(self, coroutine, timeout: float = 2):
        return self.submit(coroutine).result(timeout=timeout)

    def close(self) -> None:
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=2)
        if not self.loop.is_closed():
            self.loop.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class RecordingClient:
    def __init__(self, *, fail_first_close: bool = False):
        self.created_loop = asyncio.get_running_loop()
        self.closed_loop = None
        self.close_count = 0
        self.is_closed = False
        self.fail_first_close = fail_first_close

    async def aclose(self) -> None:
        self.close_count += 1
        self.closed_loop = asyncio.get_running_loop()
        if self.fail_first_close and self.close_count == 1:
            raise RuntimeError("injected close failure")
        self.is_closed = True


class CancellationResistantClient(RecordingClient):
    def __init__(self):
        super().__init__()
        self.release = asyncio.Event()
        self.cancellation_count = 0

    async def aclose(self) -> None:
        self.close_count += 1
        self.closed_loop = asyncio.get_running_loop()
        while not self.release.is_set():
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                self.cancellation_count += 1
        self.is_closed = True


class ClosedFlagBeforeFailureClient(RecordingClient):
    async def aclose(self) -> None:
        self.close_count += 1
        self.closed_loop = asyncio.get_running_loop()
        self.is_closed = True
        if self.close_count == 1:
            raise RuntimeError("transport close failed after closed flag")


async def leased_identity(pool):
    async with pool.lease() as client:
        return id(client)


def wait_until(predicate, timeout: float = 2) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition did not become true before timeout")


def test_pool_reuses_one_client_per_persistent_loop_a_b_a():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory)
    with LoopThread("pool-loop-a") as loop_a, LoopThread("pool-loop-b") as loop_b:
        first_a = loop_a.run(leased_identity(pool))
        first_b = loop_b.run(leased_identity(pool))
        second_a = loop_a.run(leased_identity(pool))
        asyncio.run(pool.close_all())

    assert first_a != first_b
    assert second_a == first_a
    assert len(clients) == 2


def test_concurrent_first_leases_create_one_client_on_one_loop():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    async def lease_many():
        return await asyncio.gather(*(leased_identity(pool) for _ in range(20)))

    pool = LoopClientPool(factory)
    with LoopThread("pool-loop-concurrent") as owner:
        identities = owner.run(lease_many())
        asyncio.run(pool.close_all())

    assert len(set(identities)) == 1
    assert len(clients) == 1


def test_factory_failure_is_not_cached_and_next_lease_retries():
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected factory failure")
        return RecordingClient()

    async def scenario():
        with pytest.raises(RuntimeError, match="factory failure"):
            async with pool.lease():
                pass
        return await leased_identity(pool)

    pool = LoopClientPool(factory)
    identity = asyncio.run(scenario())
    asyncio.run(pool.close_all())

    assert identity
    assert calls == 2


def test_externally_closed_client_is_replaced_only_for_its_owner_loop():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory)
    with LoopThread("pool-loop-external-close") as owner:
        first = owner.run(leased_identity(pool))
        clients[0].is_closed = True
        second = owner.run(leased_identity(pool))
        asyncio.run(pool.close_all())

    assert first != second
    assert len(clients) == 2


def test_active_lease_delays_close_and_new_leases_are_rejected():
    started = threading.Event()
    release = threading.Event()
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    async def hold_lease():
        async with pool.lease():
            started.set()
            await asyncio.to_thread(release.wait)

    async def close_scenario():
        close_task = asyncio.create_task(pool.close_all())
        await asyncio.sleep(0.02)
        with pytest.raises(PoolClosedError):
            async with pool.lease():
                pass
        assert not clients[0].is_closed
        release.set()
        await close_task

    pool = LoopClientPool(factory, drain_timeout=1, close_timeout=1)
    with LoopThread("pool-loop-active") as owner:
        holder = owner.submit(hold_lease())
        assert started.wait(2)
        asyncio.run(close_scenario())
        holder.result(timeout=2)

    assert clients[0].is_closed


def test_close_runs_each_client_on_its_owner_loop_from_third_loop():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory)
    with LoopThread("pool-loop-close-a") as loop_a, LoopThread("pool-loop-close-b") as loop_b:
        loop_a.run(leased_identity(pool))
        loop_b.run(leased_identity(pool))
        asyncio.run(pool.close_all())

        assert clients[0].closed_loop is clients[0].created_loop is loop_a.loop
        assert clients[1].closed_loop is clients[1].created_loop is loop_b.loop


def test_failed_client_is_retained_for_retry_without_blocking_other_closes():
    clients = []

    def factory():
        client = RecordingClient(fail_first_close=not clients)
        clients.append(client)
        return client

    pool = LoopClientPool(factory, close_timeout=0.5)
    with LoopThread("pool-loop-retry-a") as loop_a, LoopThread("pool-loop-retry-b") as loop_b:
        loop_a.run(leased_identity(pool))
        loop_b.run(leased_identity(pool))

        asyncio.run(pool.close_all())
        assert clients[0].close_count == 1
        assert not clients[0].is_closed
        assert clients[1].is_closed

        asyncio.run(pool.close_all())

    assert clients[0].is_closed
    assert clients[0].close_count == 2
    assert clients[1].close_count == 1


def test_failed_close_is_retried_even_when_client_set_closed_flag_first():
    clients = []

    def factory():
        client = ClosedFlagBeforeFailureClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory, close_timeout=0.5)
    with LoopThread("pool-loop-closed-before-failure") as owner:
        owner.run(leased_identity(pool))
        asyncio.run(pool.close_all())
        assert clients[0].close_count == 1

        asyncio.run(pool.close_all())

    assert clients[0].close_count == 2


def test_stopped_owner_loop_returns_within_timeout_and_retains_client():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory, close_timeout=0.05)
    owner = LoopThread("pool-loop-stopped")
    owner.run(leased_identity(pool))
    owner.close()

    started = time.monotonic()
    asyncio.run(pool.close_all())
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert not clients[0].is_closed
    assert clients[0].close_count == 0


def test_cancellation_resistant_close_keeps_one_attempt_until_task_finishes():
    clients = []

    def factory():
        client = CancellationResistantClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory, close_timeout=0.05)
    with LoopThread("pool-loop-cancel-resistant") as owner:
        owner.run(leased_identity(pool))
        asyncio.run(pool.close_all())
        assert clients[0].close_count == 1
        assert not clients[0].is_closed

        asyncio.run(pool.close_all())
        assert clients[0].close_count == 1

        owner.loop.call_soon_threadsafe(clients[0].release.set)
        wait_until(lambda: clients[0].is_closed)
        asyncio.run(pool.close_all())

    assert clients[0].close_count == 1
    assert clients[0].cancellation_count >= 1


def test_cancelled_close_waiter_does_not_cancel_internal_close_leader():
    started = threading.Event()
    release = threading.Event()
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    async def hold_lease():
        async with pool.lease():
            started.set()
            await asyncio.to_thread(release.wait)

    async def scenario():
        close_waiter = asyncio.create_task(pool.close_all())
        await asyncio.sleep(0.02)
        close_waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await close_waiter
        release.set()
        for _ in range(100):
            if clients[0].is_closed:
                break
            await asyncio.sleep(0.01)
        assert clients[0].is_closed

    pool = LoopClientPool(factory, drain_timeout=1, close_timeout=1)
    with LoopThread("pool-loop-cancel-waiter") as owner:
        holder = owner.submit(hold_lease())
        assert started.wait(2)
        asyncio.run(scenario())
        holder.result(timeout=2)


def test_drain_timeout_is_bounded_when_default_executor_is_saturated():
    clients = []

    def factory():
        client = RecordingClient()
        clients.append(client)
        return client

    pool = LoopClientPool(factory, drain_timeout=0.05, close_timeout=0.5)

    async def scenario():
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        loop.set_default_executor(executor)
        executor_release = threading.Event()
        occupied = loop.run_in_executor(None, executor_release.wait)
        loop.call_later(0.25, executor_release.set)
        try:
            async with pool.lease():
                started = time.monotonic()
                await pool.close_all()
                elapsed = time.monotonic() - started
            await occupied
        finally:
            executor_release.set()
            executor.shutdown(wait=True)
        return elapsed

    elapsed = asyncio.run(scenario())

    assert elapsed < 0.15
    assert clients[0].is_closed
