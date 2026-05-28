from __future__ import annotations

from typing import Any, Mapping


DEFAULT_JAVINFO_IMPORT_DB_SETTINGS: dict[str, Any] = {
    "host": "localhost",
    "port": 5432,
    "database": "r18",
    "maintenance_database": "postgres",
    "user": "javhub",
    "password": "",
    "max_parallel_jobs": 2,
    "keep_previous_databases": 1,
}


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(_coerce_int(value, default), maximum))


def normalize_javinfo_import_db_settings(
    settings: Mapping[str, Any] | None,
    *,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = {**DEFAULT_JAVINFO_IMPORT_DB_SETTINGS, **dict(defaults or {})}
    normalized = {**base, **dict(settings or {})}

    for key in ("host", "database", "maintenance_database", "user", "password"):
        fallback = str(base.get(key) or "").strip()
        normalized[key] = str(normalized.get(key) or fallback).strip()

    normalized["port"] = _coerce_int(normalized.get("port"), _coerce_int(base.get("port"), 5432))
    normalized["max_parallel_jobs"] = _bounded_int(
        normalized.get("max_parallel_jobs"),
        _coerce_int(base.get("max_parallel_jobs"), 2),
        1,
        8,
    )
    normalized["keep_previous_databases"] = _bounded_int(
        normalized.get("keep_previous_databases"),
        _coerce_int(base.get("keep_previous_databases"), 1),
        0,
        5,
    )
    return normalized
