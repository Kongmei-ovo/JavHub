"""Shared, long-lived event loop for async jobs triggered from sync code.

Background jobs (inventory collect/compare, subscription check, candidate
auto-process) used to each spin up a brand-new event loop via
``asyncio.new_event_loop()`` / ``asyncio.run()`` and close it when done. That
poisoned module-level singletons such as ``info_client``/``emby_client`` whose
cached ``httpx.AsyncClient`` is bound to the loop that created it: the next job
got a client bound to a *closed* loop and either hung or raised
``RuntimeError: Event loop is closed``.

This module keeps exactly one event loop alive for the whole process lifetime,
running in a dedicated daemon thread. Sync callers submit coroutines to it with
``submit`` (fire-and-forget) or ``run`` (block until done). Because every job
runs on the same persistent loop, the cached async clients stay valid and their
connection pools get reused instead of rebuilt per job.
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Coroutine

_loop: asyncio.AbstractEventLoop | None = None
_lock = threading.Lock()


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the shared background loop, starting its thread on first use."""
    global _loop
    with _lock:
        if _loop is not None and not _loop.is_closed():
            return _loop

        loop = asyncio.new_event_loop()

        def _run() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_run, name="javhub-job-loop", daemon=True)
        thread.start()
        _loop = loop
        return loop


def submit(coro: Coroutine[Any, Any, Any]) -> Future:
    """Schedule ``coro`` on the shared loop; return a concurrent Future.

    Non-blocking: use this for fire-and-forget background jobs. The returned
    Future can be awaited/`.result()`-ed from a *different* thread if the caller
    wants the outcome.
    """
    loop = get_loop()
    if _running_on_loop(loop):
        raise RuntimeError("worker_loop.submit() must not be called from the loop thread")
    return asyncio.run_coroutine_threadsafe(coro, loop)


def run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run ``coro`` on the shared loop and block until it completes.

    Drop-in replacement for ``asyncio.run(...)`` in sync code (e.g. APScheduler
    job callbacks), but without creating/closing a fresh loop each call.
    """
    return submit(coro).result()


def _running_on_loop(loop: asyncio.AbstractEventLoop) -> bool:
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False
