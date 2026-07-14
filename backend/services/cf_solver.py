"""Cloudflare challenge solver via FlareSolverr with a prewarmed session.

jable.tv / missav.ai and similar sites can return a Cloudflare challenge that
plain HTTP clients cannot solve. FlareSolverr runs headless Chrome and returns
the solved HTML. A fixed session keeps the clearance cookies between requests.
The backend warms the high-hit-rate sites in the background and refreshes them
before the idle reaper can discard the browser, keeping cold-start latency out
of the user playback path.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

import httpx

from config import Config

logger = logging.getLogger(__name__)

_SESSION_ID = "javhub-default"
_IDLE_TTL_SECONDS = 3600
_REAPER_INTERVAL_SECONDS = 60
_CONTROL_TIMEOUT_SECONDS = 30.0
_WARMUP_TARGETS = ("https://jable.tv/",)
_KEEPALIVE_TARGETS = ("https://jable.tv/", "https://missav.ai/")
_KEEPALIVE_INTERVAL_SECONDS = 1800
_INITIAL_WARMUP_DELAY_SECONDS = 60


def _configured_solver_url() -> str:
    return Config().stream_cf_solver_url.strip()


def _session_is_missing(data: dict) -> bool:
    message = str(data.get("message") or "").lower()
    return "session" in message and any(
        marker in message
        for marker in ("not found", "does not exist", "doesn't exist", "missing")
    )


class _SessionManager:
    def __init__(
        self,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        serialize_requests: bool = False,
    ) -> None:
        self.lock = asyncio.Lock()
        self.lifecycle_lock = asyncio.Lock()
        self._monotonic = monotonic
        self.closing = False
        self.created = False
        self.generation = 0
        self.active_requests = 0
        self.idle_event = asyncio.Event()
        self.idle_event.set()
        self.last_used_at: Optional[float] = None
        self.reaper_task: Optional[asyncio.Task] = None
        self.request_lock = asyncio.Lock() if serialize_requests else None

    async def start(self) -> None:
        """Discover the fixed session, then start the local idle reaper."""
        solver_url = _configured_solver_url()
        if not solver_url:
            return

        async with self.lifecycle_lock:
            if self.closing:
                await self.idle_event.wait()
            async with self.lock:
                if self.reaper_task is not None and not self.reaper_task.done():
                    return
                self.closing = False
                await self._discover_locked(solver_url)
                if self.closing:
                    return
                self.reaper_task = asyncio.create_task(
                    self._reaper_loop(),
                    name="cf-solver-session-reaper",
                )

    async def close(self) -> None:
        """Stop the reaper and make a best-effort session destroy request."""
        self.closing = True
        async with self.lifecycle_lock:
            self.closing = True
            reaper_task = self.reaper_task
            self.reaper_task = None

            if reaper_task is not None:
                reaper_task.cancel()
                try:
                    await reaper_task
                except asyncio.CancelledError:
                    current_task = asyncio.current_task()
                    if current_task is not None and current_task.cancelling():
                        raise

            await self.idle_event.wait()

            solver_url = _configured_solver_url()
            if not solver_url:
                return
            async with self.lock:
                if self.created:
                    await self._destroy_locked(solver_url)

    async def prepare(self) -> None:
        """Create the browser session without making a protected-site request."""
        solver_url = _configured_solver_url()
        if not solver_url:
            return
        async with httpx.AsyncClient(timeout=_CONTROL_TIMEOUT_SECONDS) as client:
            generation = await self._acquire_session(client, solver_url)
            if generation is not None:
                await self._release_session_safely(generation)

    async def fetch(
        self,
        url: str,
        *,
        referer: str = "",
        timeout_ms: int = 60_000,
    ) -> Optional[str]:
        solver_url = _configured_solver_url()
        if not solver_url:
            return None

        base_payload: dict = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": timeout_ms,
        }
        if referer:
            base_payload["headers"] = {"Referer": referer}

        # Leave the same ten-second margin for FlareSolverr to return its
        # browser result after its own maxTimeout expires.
        client_timeout = max((timeout_ms / 1000.0) + 10.0, 30.0)

        try:
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                # Keep the existing two-attempt contract: rebuild once when
                # FlareSolverr reports that the fixed session was lost.
                for attempt in (1, 2):
                    generation = await self._acquire_session(client, solver_url)
                    if generation is None:
                        return None
                    try:
                        payload = {**base_payload, "session": _SESSION_ID}
                        if self.request_lock is None:
                            response = await client.post(solver_url, json=payload)
                        else:
                            async with self.request_lock:
                                response = await client.post(solver_url, json=payload)
                        if response.status_code != 200:
                            logger.warning("FlareSolverr HTTP %s", response.status_code)
                            return None
                        data = response.json()
                        message = str(data.get("message") or "").lower()
                        if data.get("status") != "ok":
                            if "session" in message:
                                await self._mark_session_lost(generation)
                                if attempt == 1:
                                    logger.info(
                                        "FlareSolverr session lost, rebuilding"
                                    )
                                    continue
                            logger.warning(
                                "FlareSolverr non-ok for %s: %s",
                                url,
                                data.get("message"),
                            )
                            return None
                        solution = data.get("solution") or {}
                        if solution.get("status") != 200:
                            logger.info(
                                "CF solver upstream %s -> %s",
                                url,
                                solution.get("status"),
                            )
                            return None
                        return solution.get("response")
                    finally:
                        await self._release_session_safely(generation)
        except Exception as exc:
            logger.warning("FlareSolverr request failed for %s: %s", url, exc)
            return None
        return None

    async def _discover_locked(self, solver_url: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=_CONTROL_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    solver_url,
                    json={"cmd": "sessions.list"},
                )
            data = response.json() if response.status_code == 200 else {}
        except Exception as exc:
            logger.warning("FlareSolverr sessions.list failed: %s", exc)
            return

        if data.get("status") != "ok":
            logger.warning("FlareSolverr sessions.list non-ok: %s", data.get("message"))
            return

        self.generation += 1
        self.created = _SESSION_ID in (data.get("sessions") or [])
        self.last_used_at = self._monotonic() if self.created else None

    async def _acquire_session(
        self,
        client: httpx.AsyncClient,
        solver_url: str,
    ) -> Optional[int]:
        async with self.lock:
            if self.closing:
                return None
            if not self.created and not await self._create_locked(client, solver_url):
                return None
            if self.closing:
                return None
            if self.active_requests == 0:
                self.idle_event.clear()
            self.active_requests += 1
            return self.generation

    async def _create_locked(
        self,
        client: httpx.AsyncClient,
        solver_url: str,
    ) -> bool:
        try:
            response = await client.post(
                solver_url,
                json={"cmd": "sessions.create", "session": _SESSION_ID},
            )
            data = response.json() if response.status_code == 200 else {}
        except Exception as exc:
            logger.warning("FlareSolverr session.create failed: %s", exc)
            return False

        if data.get("status") != "ok":
            logger.warning("FlareSolverr session.create non-ok: %s", data.get("message"))
            return False

        self.created = True
        self.generation += 1
        self.last_used_at = self._monotonic()
        logger.info("FlareSolverr session %s ready", _SESSION_ID)
        return True

    async def _release_session_safely(self, generation: int) -> None:
        release_task = asyncio.create_task(self._release_session(generation))
        try:
            await asyncio.shield(release_task)
        except asyncio.CancelledError:
            await release_task
            raise

    async def _release_session(self, generation: int) -> None:
        async with self.lock:
            if self.active_requests <= 0:
                raise RuntimeError("FlareSolverr active request count underflow")
            self.active_requests -= 1
            if self.created and generation == self.generation:
                self.last_used_at = self._monotonic()
            if self.active_requests == 0:
                self.idle_event.set()

    async def _mark_session_lost(self, generation: int) -> None:
        async with self.lock:
            if self.created and generation == self.generation:
                self.created = False
                self.last_used_at = None

    async def _reaper_loop(self) -> None:
        while True:
            await asyncio.sleep(_REAPER_INTERVAL_SECONDS)
            try:
                await self._reap_if_idle()
            except Exception as exc:
                logger.warning("FlareSolverr idle reaper failed: %s", exc)

    async def is_busy(self) -> bool:
        async with self.lock:
            return self.active_requests > 0

    async def _reap_if_idle(self) -> None:
        if self.closing:
            return
        solver_url = _configured_solver_url()
        if not solver_url:
            return

        async with self.lock:
            if (
                self.closing
                or not self.created
                or self.active_requests != 0
                or self.last_used_at is None
                or self._monotonic() - self.last_used_at < _IDLE_TTL_SECONDS
            ):
                return
            await self._destroy_locked(solver_url)

    async def _destroy_locked(self, solver_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=_CONTROL_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    solver_url,
                    json={"cmd": "sessions.destroy", "session": _SESSION_ID},
                )
            data = response.json()
        except Exception as exc:
            logger.warning("FlareSolverr sessions.destroy failed: %s", exc)
            return False

        if (
            200 <= response.status_code < 300 and data.get("status") == "ok"
        ) or _session_is_missing(data):
            self.created = False
            self.last_used_at = None
            logger.info("FlareSolverr session %s destroyed", _SESSION_ID)
            return True

        logger.warning("FlareSolverr sessions.destroy non-ok: %s", data.get("message"))
        return False


_session_manager = _SessionManager(serialize_requests=True)
_warmup_task: Optional[asyncio.Task] = None


async def _warm_targets(targets: tuple[str, ...]) -> None:
    for url in targets:
        if await _session_manager.is_busy():
            logger.debug("Skipping CF solver keepalive while playback lookup is active")
            break
        try:
            html = await _session_manager.fetch(url, timeout_ms=90_000)
            if html is None:
                logger.warning("CF solver warmup returned no page for %s", url)
            else:
                logger.info("CF solver warmup ready: %s", url)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("CF solver warmup failed for %s: %s", url, exc)


async def _warmup_and_keepalive() -> None:
    """Defer network warmup so startup playback always has browser priority."""
    await asyncio.sleep(_INITIAL_WARMUP_DELAY_SECONDS)
    await _warm_targets(_WARMUP_TARGETS)
    while True:
        await asyncio.sleep(_KEEPALIVE_INTERVAL_SECONDS)
        await _warm_targets(_KEEPALIVE_TARGETS)


async def start_session_manager() -> None:
    global _warmup_task
    await _session_manager.start()
    if not _configured_solver_url():
        return
    await _session_manager.prepare()
    if _warmup_task is None or _warmup_task.done():
        _warmup_task = asyncio.create_task(
            _warmup_and_keepalive(),
            name="cf-solver-warmup",
        )


async def close_session_manager() -> None:
    global _warmup_task
    task = _warmup_task
    _warmup_task = None
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await _session_manager.close()


async def fetch_with_cf_solver(
    url: str,
    *,
    referer: str = "",
    timeout_ms: int = 60_000,
) -> Optional[str]:
    """Fetch solved HTML through FlareSolverr, returning None on failure."""
    return await _session_manager.fetch(
        url,
        referer=referer,
        timeout_ms=timeout_ms,
    )
