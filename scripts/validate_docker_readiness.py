#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from typing import Any


def _require(condition: bool, field: str, actual: Any) -> None:
    if not condition:
        raise AssertionError(f"{field} check failed: {actual!r}")


def validate_readiness(payload: dict[str, Any]) -> None:
    config = payload.get("config") or {}
    database = payload.get("database") or {}
    javinfo = payload.get("javinfo") or {}
    cache = payload.get("cache") or {}
    downloaders = payload.get("downloaders") or {}
    sources = payload.get("sources") or {}
    scheduler = payload.get("scheduler") or {}

    _require(config.get("loaded") is True, "config.loaded", config.get("loaded"))
    _require(not config.get("error"), "config.error", config.get("error"))
    _require(
        database.get("connectable") is True,
        "database.connectable",
        database.get("connectable"),
    )
    _require(not database.get("error"), "database.error", database.get("error"))
    _require(
        javinfo.get("api_url_configured") is True,
        "javinfo.api_url_configured",
        javinfo.get("api_url_configured"),
    )
    _require(javinfo.get("legacy") is False, "javinfo.legacy", javinfo.get("legacy"))
    _require(
        javinfo.get("reachable") is True,
        "javinfo.reachable",
        javinfo.get("reachable"),
    )
    _require(not javinfo.get("error"), "javinfo.error", javinfo.get("error"))
    _require(cache.get("backend") == "redis", "cache.backend", cache.get("backend"))
    _require(not cache.get("error"), "cache.error", cache.get("error"))
    _require(not downloaders.get("error"), "downloaders.error", downloaders.get("error"))
    _require(not sources.get("error"), "sources.error", sources.get("error"))
    _require(not scheduler.get("error"), "scheduler.error", scheduler.get("error"))

    status = payload.get("status")
    expected_status = (
        "ok"
        if downloaders.get("default_available") is True
        else "degraded"
    )
    _require(status == expected_status, "status", status)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise AssertionError(f"payload check failed: {type(payload).__name__}")
        validate_readiness(payload)
    except Exception as exc:
        print(f"readiness smoke failed: {exc}", file=sys.stderr)
        return 1
    print("readiness smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
