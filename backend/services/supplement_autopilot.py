"""Supplement autopilot: keep per-actress supplement data populated.

The JavInfoApi side already has the full merge machinery (supplement_movies +
matcher + resolved_videos), but nothing used to *drive* it — an actress could
be subscribed for months with ``supplement_movies = 0`` while JavHub silently
fell back to the plain r18 view. This module is the missing driver:

- ``ensure_actress_supplement``: create a filmography supplement job for one
  actress (the JavInfoApi job runner upserts source items, matches them and
  refreshes ``resolved_videos`` at the end, so a single POST is enough).
- A per-actress monotonic TTL prevents hammering the upstream scrapers; the
  JavInfoApi job repository additionally dedupes active jobs server-side, so
  concurrent callers are safe.

Hooked from:
- subscription checks (``services.subscription``) — every actress-scope check
  first makes sure her supplement data exists/refreshes on the TTL cadence;
- the actress videos route — a ``supplement_pending`` fallback schedules a
  background ensure so visiting a page heals the data.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# One filmography scrape per actress per TTL window is plenty: subscriptions
# run on their own cadence and new releases don't appear hourly.
DEFAULT_ENSURE_TTL_SECONDS = 6 * 3600
DEFAULT_SOURCE = "avbase"

_last_attempts: dict[int, float] = {}
_attempts_lock = asyncio.Lock()


def _now() -> float:
    return time.monotonic()


async def _claim_attempt(actress_id: int, ttl_seconds: float, force: bool) -> bool:
    async with _attempts_lock:
        last = _last_attempts.get(actress_id)
        if not force and last is not None and _now() - last < ttl_seconds:
            return False
        _last_attempts[actress_id] = _now()
        return True


async def _release_attempt(actress_id: int) -> None:
    async with _attempts_lock:
        _last_attempts.pop(actress_id, None)


def reset_attempt_cache() -> None:
    """Test helper: forget all TTL claims."""
    _last_attempts.clear()


async def ensure_actress_supplement(
    actress_id: int,
    *,
    source: str = DEFAULT_SOURCE,
    ttl_seconds: float = DEFAULT_ENSURE_TTL_SECONDS,
    force: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    """Make sure the supplement pipeline has run (recently) for an actress.

    Returns an action report; never raises (failures release the TTL claim so
    the next caller retries).
    """
    if not actress_id or int(actress_id) <= 0:
        return {"action": "skipped_invalid", "actress_id": actress_id}
    actress_id = int(actress_id)

    if not await _claim_attempt(actress_id, ttl_seconds, force):
        return {"action": "skipped_recent", "actress_id": actress_id}

    if client is None:
        from modules.info_client import get_info_client
        client = get_info_client()

    try:
        job = await client.proxy_post(
            f"/api/v1/supplement/actresses/{actress_id}/filmography/jobs",
            params={"source": source},
        )
    except Exception as exc:  # noqa: BLE001 - autopilot must never break callers
        await _release_attempt(actress_id)
        logger.warning(
            "[SupplementAutopilot] filmography job creation failed for actress %s: %s",
            actress_id,
            exc,
        )
        return {"action": "job_failed", "actress_id": actress_id, "error": str(exc)}

    existing = bool(isinstance(job, dict) and job.get("existing"))
    logger.info(
        "[SupplementAutopilot] filmography job %s for actress %s (source=%s, existing=%s)",
        (job or {}).get("job_id"),
        actress_id,
        source,
        existing,
    )
    return {
        "action": "job_exists" if existing else "job_created",
        "actress_id": actress_id,
        "job": job,
    }


def schedule_actress_supplement(
    actress_id: int,
    *,
    source: str = DEFAULT_SOURCE,
    ttl_seconds: float = DEFAULT_ENSURE_TTL_SECONDS,
) -> bool:
    """Fire-and-forget ensure for request-path callers. Returns True if scheduled."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    loop.create_task(
        ensure_actress_supplement(actress_id, source=source, ttl_seconds=ttl_seconds)
    )
    return True
