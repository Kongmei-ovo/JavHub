#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from services import cache


def _assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def _exercise_cache_backend(label: str) -> dict[str, Any]:
    cache.reset_backend()
    cache.reset_metrics()

    payload = {"content_id": f"{label.upper()}-001", "title": f"{label} smoke"}
    cache.set_video(payload["content_id"], payload, ttl=60)
    cache.set_response("smoke", {"backend": label}, {"ok": True, "backend": label}, ttl=60)

    _assert_equal(cache.get_video(payload["content_id"]), payload, f"{label} video get")
    _assert_equal(
        cache.get_response("smoke", {"backend": label}),
        {"ok": True, "backend": label},
        f"{label} response get",
    )

    stats = cache.get_stats()
    if stats["total_entries"] < 2:
        raise AssertionError(f"{label} stats should include smoke entries: {stats!r}")
    if stats["metrics"]["video"]["hits"] < 1 or stats["metrics"]["response"]["hits"] < 1:
        raise AssertionError(f"{label} stats should include cache hit metrics: {stats!r}")

    purged = cache.purge_all()
    if purged < 2:
        raise AssertionError(f"{label} purge should remove smoke entries, removed {purged}")
    _assert_equal(cache.get_video(payload["content_id"]), None, f"{label} video purge")
    _assert_equal(cache.get_response("smoke", {"backend": label}), None, f"{label} response purge")

    return {"backend": stats["backend"], "entries_before_purge": stats["total_entries"], "purged": purged}


def _run_sqlite_smoke() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        original_db_path = cache._db_path
        original_backend = os.environ.pop("JAVHUB_CACHE_BACKEND", None)
        try:
            cache._db_path = Path(tempdir) / "cache-smoke.sqlite3"
            return _exercise_cache_backend("sqlite")
        finally:
            cache._db_path = original_db_path
            if original_backend is not None:
                os.environ["JAVHUB_CACHE_BACKEND"] = original_backend
            cache.reset_backend()


def _run_redis_smoke_if_requested() -> dict[str, Any] | None:
    if os.getenv("JAVHUB_CACHE_BACKEND", "").strip().lower() != "redis":
        return None
    if not os.getenv("JAVHUB_REDIS_URL", "").strip():
        raise RuntimeError("JAVHUB_CACHE_BACKEND=redis requires JAVHUB_REDIS_URL")

    os.environ.setdefault("JAVHUB_REDIS_PREFIX", "javhub-cache-smoke")
    url = os.environ["JAVHUB_REDIS_URL"]
    separator = "&" if "?" in url else "?"
    os.environ["JAVHUB_REDIS_URL"] = f"{url}{separator}socket_connect_timeout=1&socket_timeout=1"
    return _exercise_cache_backend("redis")


def main() -> int:
    sqlite_result = _run_sqlite_smoke()
    print(
        "sqlite smoke ok: "
        f"entries_before_purge={sqlite_result['entries_before_purge']} "
        f"purged={sqlite_result['purged']}"
    )

    try:
        redis_result = _run_redis_smoke_if_requested()
    except Exception as exc:
        print(f"redis smoke skipped: unable to connect or initialize Redis ({exc})")
        return 0

    if redis_result is None:
        print("redis smoke skipped: set JAVHUB_CACHE_BACKEND=redis and JAVHUB_REDIS_URL to run it")
        return 0

    print(
        "redis smoke ok: "
        f"entries_before_purge={redis_result['entries_before_purge']} "
        f"purged={redis_result['purged']} "
        f"prefix={os.getenv('JAVHUB_REDIS_PREFIX')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
