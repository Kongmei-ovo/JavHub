import asyncio
from typing import Any

import httpx
from fastapi import APIRouter

from config import LEGACY_JAVINFO_API_URLS, config
from database.base import get_db_orig
from services import cache
from services.open115 import open115_binding_status

router = APIRouter(tags=["health"])


def _error_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


def _config_status() -> dict[str, Any]:
    return {
        "loaded": bool(config.config_loaded),
        "error": str(config.config_load_error or ""),
        "path": str(config.config_path),
    }


def _database_status() -> dict[str, Any]:
    db_cfg = config.javhub_database
    result = {
        "backend": "postgres",
        "connectable": False,
        "host": str(db_cfg.get("host") or ""),
        "port": int(db_cfg.get("port") or 5432),
        "database": str(db_cfg.get("database") or ""),
        "user": str(db_cfg.get("user") or ""),
        "error": "",
    }
    conn = None
    try:
        conn = get_db_orig()
        conn.execute("SELECT 1")
        result["connectable"] = True
    except Exception as exc:
        result["error"] = _error_message(exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return result


async def _probe_javinfo(api_url: str) -> dict[str, Any]:
    if not api_url:
        return {"reachable": False, "version": "", "error": "api url not configured"}
    try:
        async with httpx.AsyncClient(timeout=2, follow_redirects=True) as client:
            response = await client.get(f"{api_url.rstrip('/')}/health")
            response.raise_for_status()
            version = ""
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    version = str(payload.get("version") or payload.get("app_version") or "")
            except Exception:
                version = ""
            return {"reachable": True, "version": version, "error": ""}
    except Exception as exc:
        return {"reachable": False, "version": "", "error": _error_message(exc)}


async def _javinfo_status() -> dict[str, Any]:
    api_url = str(config.javinfo_api_url or "").strip()
    status = {
        "api_url_configured": bool(api_url),
        "api_url": api_url,
        "legacy": api_url.rstrip("/") in LEGACY_JAVINFO_API_URLS,
    }
    status.update(await _probe_javinfo(api_url))
    if status["legacy"] and not status["error"]:
        status["error"] = "legacy api url"
    return status


def _cache_status() -> dict[str, Any]:
    try:
        stats = cache.get_stats()
    except Exception as exc:
        return {
            "backend": "unknown",
            "active_entries": None,
            "expired_entries": None,
            "total_entries": None,
            "singleflight_locks": None,
            "error": _error_message(exc),
        }
    return {
        "backend": str(stats.get("backend") or "unknown"),
        "active_entries": stats.get("active_entries"),
        "expired_entries": stats.get("expired_entries"),
        "total_entries": stats.get("total_entries"),
        "singleflight_locks": stats.get("singleflight_locks"),
        "error": "",
    }


def _downloader_summary() -> dict[str, Any]:
    try:
        raw = config._config.get("downloaders", {}) if isinstance(config._config, dict) else {}
        clients = raw.get("clients") if isinstance(raw, dict) else []
        if not isinstance(clients, list):
            clients = []
        clients = [
            item for item in clients
            if isinstance(item, dict)
            and str(item.get("type") or "").lower() not in {"openlist", "open115"}
        ]
        open115 = config._config.get("open115", {}) if isinstance(config._config, dict) else {}
        if not isinstance(open115, dict):
            open115 = {}
        binding = open115_binding_status(open115)
        clients.insert(0, {
            "id": "open115",
            "type": "open115",
            "enabled": binding["verified"],
        })
        default_id = str(raw.get("default_id") or "") if isinstance(raw, dict) else ""
        if default_id == "openlist":
            default_id = "open115"
        selected = next((item for item in clients if str(item.get("id") or "") == default_id), None)
        if not selected or not bool(selected.get("enabled")):
            default = next((item for item in clients if bool(item.get("enabled"))), None)
            default_id = str(default.get("id") or "") if default else ""
        default = next((item for item in clients if isinstance(item, dict) and item.get("id") == default_id), None)
        available = [item for item in clients if isinstance(item, dict) and bool(item.get("enabled"))]
        return {
            "default_id": default_id,
            "default_available": bool(default and default.get("enabled")),
            "registered": len(clients),
            "available": len(available),
            "error": "",
        }
    except Exception as exc:
        return {
            "default_id": "",
            "default_available": False,
            "registered": 0,
            "available": 0,
            "error": _error_message(exc),
        }


def _source_registry_summary() -> dict[str, Any]:
    try:
        from sources import register_all_sources
        from sources.registry import SourceRegistry

        register_all_sources()
        sources = SourceRegistry.all()
        available = [
            source for source in sources
            if not callable(getattr(source, "is_implemented", None)) or source.is_implemented()
        ]
        return {
            "registered": len(sources),
            "available": len(available),
            "error": "",
            **_source_attempt_summary(),
        }
    except Exception as exc:
        return {
            "registered": 0,
            "available": 0,
            "error": _error_message(exc),
            **_empty_source_attempt_summary(),
        }


def _empty_source_attempt_summary() -> dict[str, Any]:
    return {
        "recent_attempt_count": 0,
        "latest_attempt_error": "",
        "latest_attempt_source": "",
        "latest_attempt_keyword": "",
    }


def _with_source_attempt_defaults(status: dict[str, Any]) -> dict[str, Any]:
    return {
        **status,
        **{
            key: status.get(key, value)
            for key, value in _empty_source_attempt_summary().items()
        },
    }


def _source_attempt_summary(limit: int = 20) -> dict[str, Any]:
    try:
        from sources.registry import SourceRegistry

        attempts = SourceRegistry.recent_attempts(limit=limit)
    except Exception:
        return _empty_source_attempt_summary()
    latest_error = next((item for item in reversed(attempts) if item.get("error")), None)
    if not latest_error:
        return {
            **_empty_source_attempt_summary(),
            "recent_attempt_count": len(attempts),
        }
    return {
        "recent_attempt_count": len(attempts),
        "latest_attempt_error": str(latest_error.get("error") or ""),
        "latest_attempt_source": str(latest_error.get("source") or ""),
        "latest_attempt_keyword": str(latest_error.get("keyword") or ""),
    }


def _scheduler_summary() -> dict[str, Any]:
    try:
        from scheduler.tasks import candidate_auto_process_schedule_state

        state = candidate_auto_process_schedule_state()
    except Exception as exc:
        message = _error_message(exc)
        state = {
            "enabled": False,
            "running": False,
            "next_run_time": None,
            "error": message,
        }

    policy = str(getattr(config, "automation_download_policy", "manual") or "manual").lower()
    enabled = bool(state.get("enabled"))
    disabled_reason = str(state.get("error") or "")
    if policy == "manual":
        effective_enabled = False
        disabled_reason = disabled_reason or "manual_policy"
    elif not enabled:
        effective_enabled = False
        disabled_reason = disabled_reason or "schedule_disabled"
    else:
        effective_enabled = True
    return {
        **state,
        "policy": policy,
        "effective_enabled": effective_enabled,
        "disabled_reason": disabled_reason,
    }


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/readiness")
async def readiness_check():
    config_status = _config_status()
    (
        database_status,
        javinfo_status,
        cache_status,
        downloader_status,
        sources_status,
        scheduler_status,
    ) = await asyncio.gather(
        asyncio.to_thread(_database_status),
        _javinfo_status(),
        asyncio.to_thread(_cache_status),
        asyncio.to_thread(_downloader_summary),
        asyncio.to_thread(lambda: _with_source_attempt_defaults(_source_registry_summary())),
        asyncio.to_thread(_scheduler_summary),
    )

    degraded = (
        not config_status["loaded"]
        or not database_status["connectable"]
        or not javinfo_status["api_url_configured"]
        or bool(javinfo_status["legacy"])
        or not javinfo_status["reachable"]
        or bool(cache_status["error"])
        or not downloader_status["default_available"]
        or bool(downloader_status["error"])
        or bool(sources_status["error"])
        or bool(scheduler_status.get("error"))
    )
    return {
        "status": "degraded" if degraded else "ok",
        "config": config_status,
        "database": database_status,
        "javinfo": javinfo_status,
        "cache": cache_status,
        "downloaders": downloader_status,
        "sources": sources_status,
        "scheduler": scheduler_status,
    }
