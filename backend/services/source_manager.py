from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import uuid
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from config import DEFAULT_TORZNAB_SOURCE, config
from database.avdb import get_avdb_status


logger = logging.getLogger(__name__)

LEGACY_TORZNAB_ID = "torznab-primary"

_SOURCE_WRITE_LOCK = threading.RLock()
_RESERVED_SOURCE_IDS = frozenset({LEGACY_TORZNAB_ID, "avdb", "m3u8"})
_AVDB_PUBLIC_STATUS_FIELDS = (
    "available",
    "status",
    "version",
    "count",
    "time",
    "error",
    "current_release",
    "current_generation",
    "asset_fingerprint",
    "record_count",
    "source_counts",
    "import_stats",
    "last_checked_at",
    "last_started_at",
    "last_completed_at",
    "last_error",
)


class SourceConfigError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = int(status_code)


def get_source_snapshot(*, avdb_status: dict | None = None) -> dict:
    sources = _saved_sources()
    status = _read_avdb_status() if avdb_status is None else _status_dict(avdb_status)
    public_sources: list[dict[str, Any]] = []

    legacy = sources.get("torznab")
    if isinstance(legacy, dict) and _text(legacy.get("base_url")):
        public_sources.append(
            _public_torznab(legacy, source_id=LEGACY_TORZNAB_ID, runtime_index=1)
        )

    instances = sources.get("torznab_instances")
    if isinstance(instances, list):
        resolved_ids = _resolved_instance_ids(instances)
        for position, item in enumerate(instances):
            if not isinstance(item, dict):
                continue
            source_id = resolved_ids[position]
            if source_id is None:
                continue
            public_sources.append(
                _public_torznab(
                    item,
                    source_id=source_id,
                    runtime_index=position + 2,
                )
            )

    avdb = sources.get("avdb")
    if isinstance(avdb, dict) and _as_bool(avdb.get("sync_enabled"), default=False):
        public_sources.append(_public_avdb(avdb, status))

    return {
        "builtins": [
            {
                "id": "m3u8",
                "type": "m3u8",
                "name": "在线 M3U8",
                "builtin": True,
                "enabled": True,
                "available": True,
            }
        ],
        "sources": public_sources,
        "types": ["torznab", "avdb"],
    }


def create_source(payload: dict) -> dict:
    body = _payload_dict(payload)
    source_type = _text(body.get("type")).casefold()
    with _SOURCE_WRITE_LOCK, config._write_lock:
        sources = _sources_for_write()
        if source_type == "torznab":
            item = _new_torznab(body, sources)
            instances = sources.get("torznab_instances")
            if not isinstance(instances, list):
                instances = []
                sources["torznab_instances"] = instances
            instances.append(item)
            return _persist_sources(sources, avdb_changed=False)
        if source_type == "avdb":
            avdb = sources.get("avdb")
            current = avdb if isinstance(avdb, dict) else {}
            if _as_bool(current.get("sync_enabled"), default=False):
                raise SourceConfigError("AVDB 来源已存在", status_code=409)
            sources["avdb"] = {
                **current,
                "enabled": False,
                "sync_enabled": True,
            }
            return _persist_sources(sources, avdb_changed=True)
        raise SourceConfigError("不支持的来源类型", status_code=400)


def update_source(source_id: str, payload: dict) -> dict:
    normalized_id = _text(source_id)
    body = _payload_dict(payload)
    with _SOURCE_WRITE_LOCK, config._write_lock:
        sources = _sources_for_write()
        if normalized_id == "avdb":
            avdb = sources.get("avdb")
            if not isinstance(avdb, dict) or not _as_bool(
                avdb.get("sync_enabled"), default=False
            ):
                raise SourceConfigError("来源不存在", status_code=404)
            status: dict | None = None
            enabled = _as_bool(body.get("enabled"), default=_as_bool(avdb.get("enabled")))
            if enabled:
                status = _read_avdb_status()
                if not _as_bool(status.get("available"), default=False):
                    raise SourceConfigError("AVDB 数据尚不可用，无法启用", status_code=400)
            sources["avdb"] = {**avdb, "enabled": enabled, "sync_enabled": True}
            return _persist_sources(
                sources,
                avdb_changed=True,
                avdb_status=status,
            )

        target = _find_torznab(sources, normalized_id)
        if target is None:
            raise SourceConfigError("来源不存在", status_code=404)
        location, position, current = target
        updated = _updated_torznab(current, body)
        _validate_torznab(updated, sources, exclude_id=normalized_id)
        if location == "legacy":
            sources["torznab"] = updated
        else:
            sources["torznab_instances"][position] = updated
        return _persist_sources(sources, avdb_changed=False)


def delete_source(source_id: str) -> dict:
    normalized_id = _text(source_id)
    with _SOURCE_WRITE_LOCK, config._write_lock:
        sources = _sources_for_write()
        if normalized_id == "avdb":
            avdb = sources.get("avdb")
            if not isinstance(avdb, dict) or not _as_bool(
                avdb.get("sync_enabled"), default=False
            ):
                raise SourceConfigError("来源不存在", status_code=404)
            sources["avdb"] = {
                **avdb,
                "enabled": False,
                "sync_enabled": False,
            }
            return _persist_sources(sources, avdb_changed=True)

        target = _find_torznab(sources, normalized_id)
        if target is None:
            raise SourceConfigError("来源不存在", status_code=404)
        location, position, _current = target
        if location == "legacy":
            sources["torznab"] = copy.deepcopy(DEFAULT_TORZNAB_SOURCE)
        else:
            del sources["torznab_instances"][position]
        return _persist_sources(sources, avdb_changed=False)


def source_runtime_name(source_id: str) -> str | None:
    normalized_id = _text(source_id)
    sources = _saved_sources()
    if normalized_id == "avdb":
        avdb = sources.get("avdb")
        if not isinstance(avdb, dict):
            return None
        if not _as_bool(avdb.get("sync_enabled"), default=False):
            return None
        if not _as_bool(avdb.get("enabled"), default=False):
            return None
        if not _as_bool(_read_avdb_status().get("available"), default=False):
            return None
        return "avdb"

    target = _find_torznab(sources, normalized_id)
    if target is None:
        return None
    location, position, item = target
    runtime_index = 1 if location == "legacy" else position + 2
    runtime = config._normalize_torznab_source_config(item, runtime_index)
    if not runtime["enabled"] or not runtime["base_url"] or not runtime["api_key"]:
        return None
    return runtime["name"]


def _saved_sources() -> dict:
    raw = config._config.get("sources", {})
    return raw if isinstance(raw, dict) else {}


def _sources_for_write() -> dict:
    sources = copy.deepcopy(_saved_sources())
    _materialize_instance_ids(sources)
    return sources


def _materialize_instance_ids(sources: dict) -> None:
    instances = sources.get("torznab_instances")
    if not isinstance(instances, list):
        return
    resolved_ids = _resolved_instance_ids(instances)
    for position, item in enumerate(instances):
        if not isinstance(item, dict):
            continue
        item["id"] = resolved_ids[position]


def _resolved_instance_ids(instances: list) -> list[str | None]:
    original_ids = Counter(
        _text(item.get("id"))
        for item in instances
        if isinstance(item, dict) and _text(item.get("id"))
    )
    preserved_ids = {
        source_id
        for source_id, count in original_ids.items()
        if count == 1 and source_id not in _RESERVED_SOURCE_IDS
    }
    used = set(_RESERVED_SOURCE_IDS) | preserved_ids
    resolved: list[str | None] = []
    for position, item in enumerate(instances):
        if not isinstance(item, dict):
            resolved.append(None)
            continue
        existing = _text(item.get("id"))
        if existing in preserved_ids:
            source_id = existing
        else:
            source_id = _compatible_instance_id(item, position, used)
        used.add(source_id)
        resolved.append(source_id)
    return resolved


def _compatible_instance_id(item: dict, position: int, used: set[str]) -> str:
    runtime = config._normalize_torznab_source_config(item, position + 2)
    canonical = {
        "position": position,
        "kind": _torznab_kind(item),
        "enabled": runtime["enabled"],
        "name": runtime["name"],
        "base_url": runtime["base_url"],
        "indexer": runtime["indexer"],
        "categories": runtime["categories"],
        "limit": runtime["limit"],
        "timeout": runtime["timeout"],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    collision = 0
    while True:
        suffix = b"" if collision == 0 else f":{collision}".encode("ascii")
        digest = hashlib.sha256(encoded + suffix).hexdigest()[:16]
        candidate = f"torznab-legacy-{digest}"
        if candidate not in used:
            return candidate
        collision += 1


def _find_torznab(sources: dict, source_id: str) -> tuple[str, int, dict] | None:
    legacy = sources.get("torznab")
    if (
        source_id == LEGACY_TORZNAB_ID
        and isinstance(legacy, dict)
        and _text(legacy.get("base_url"))
    ):
        return "legacy", -1, legacy
    instances = sources.get("torznab_instances")
    if not isinstance(instances, list):
        return None
    resolved_ids = _resolved_instance_ids(instances)
    for position, item in enumerate(instances):
        if isinstance(item, dict) and resolved_ids[position] == source_id:
            return "instance", position, item
    return None


def _new_torznab(payload: dict, sources: dict) -> dict:
    configured_key = _text(payload.get("api_key"))
    item = {
        "id": _new_source_id(sources),
        "kind": _torznab_kind(payload),
        "enabled": _as_bool(payload.get("enabled"), default=False),
        "name": _text(payload.get("name")),
        "base_url": _text(payload.get("base_url")),
        "api_key": configured_key,
        "indexer": _text(payload.get("indexer")) or "all",
        "categories": _text(payload.get("categories")),
        "limit": config._clamp_int(payload.get("limit"), 20, 1, 100),
        "timeout": config._clamp_int(payload.get("timeout"), 15, 1, 60),
    }
    _validate_torznab(item, sources)
    return item


def _updated_torznab(current: dict, payload: dict) -> dict:
    updated = copy.deepcopy(current)
    updated["enabled"] = _as_bool(
        payload.get("enabled"),
        default=_as_bool(current.get("enabled"), default=False),
    )
    updated["name"] = _text(payload.get("name", current.get("name")))
    updated["base_url"] = _text(payload.get("base_url", current.get("base_url")))
    if "kind" in payload:
        updated["kind"] = _torznab_kind(payload)
    if _text(payload.get("api_key")):
        updated["api_key"] = _text(payload.get("api_key"))
    updated["indexer"] = _text(payload.get("indexer", current.get("indexer"))) or "all"
    updated["categories"] = _text(payload.get("categories", current.get("categories")))
    updated["limit"] = config._clamp_int(
        payload.get("limit", current.get("limit")),
        20,
        1,
        100,
    )
    updated["timeout"] = config._clamp_int(
        payload.get("timeout", current.get("timeout")),
        15,
        1,
        60,
    )
    return updated


def _validate_torznab(item: dict, sources: dict, *, exclude_id: str | None = None) -> None:
    name = _text(item.get("name"))
    if not name:
        raise SourceConfigError("来源名称不能为空", status_code=400)
    item["name"] = name
    if name.casefold() == "avdb":
        raise SourceConfigError("名称 AVDB 保留给系统来源", status_code=409)
    _validate_unique_name(sources, name, exclude_id=exclude_id)

    base_url = _text(item.get("base_url"))
    if not _is_http_url(base_url):
        raise SourceConfigError("Torznab 地址必须是有效的 HTTP(S) URL", status_code=400)
    item["base_url"] = base_url

    if not _text(item.get("api_key")) and not _text(os.getenv("JAVHUB_TORZNAB_API_KEY")):
        raise SourceConfigError("Torznab API Key 未配置", status_code=400)


def _validate_unique_name(sources: dict, name: str, *, exclude_id: str | None) -> None:
    normalized = name.strip().casefold()
    legacy = sources.get("torznab")
    if isinstance(legacy, dict) and _text(legacy.get("base_url")):
        legacy_name = config._normalize_torznab_source_config(legacy, 1)["name"]
        if exclude_id != LEGACY_TORZNAB_ID and legacy_name.casefold() == normalized:
            raise SourceConfigError("来源名称已存在", status_code=409)
    instances = sources.get("torznab_instances")
    if not isinstance(instances, list):
        return
    resolved_ids = _resolved_instance_ids(instances)
    for position, item in enumerate(instances):
        if not isinstance(item, dict):
            continue
        item_id = resolved_ids[position]
        if item_id == exclude_id:
            continue
        runtime_name = config._normalize_torznab_source_config(item, position + 2)["name"]
        if runtime_name.casefold() == normalized:
            raise SourceConfigError("来源名称已存在", status_code=409)


def _new_source_id(sources: dict) -> str:
    reserved = set(_RESERVED_SOURCE_IDS)
    instances = sources.get("torznab_instances")
    if isinstance(instances, list):
        reserved.update(
            source_id
            for source_id in _resolved_instance_ids(instances)
            if source_id is not None
        )
    while True:
        candidate = uuid.uuid4().hex
        if candidate not in reserved:
            return candidate


def _public_torznab(item: dict, *, source_id: str, runtime_index: int) -> dict:
    runtime = config._normalize_torznab_source_config(item, runtime_index)
    return {
        "id": source_id,
        "type": "torznab",
        "kind": _torznab_kind(item),
        "enabled": runtime["enabled"],
        "name": runtime["name"],
        "base_url": runtime["base_url"],
        "indexer": runtime["indexer"],
        "categories": runtime["categories"],
        "limit": runtime["limit"],
        "timeout": runtime["timeout"],
        "api_key_configured": bool(runtime["api_key"]),
    }


def _public_avdb(avdb: dict, status: dict) -> dict:
    public_status = {
        key: copy.deepcopy(status[key])
        for key in _AVDB_PUBLIC_STATUS_FIELDS
        if key in status
    }
    return {
        **public_status,
        "id": "avdb",
        "type": "avdb",
        "name": "avdb",
        "enabled": _as_bool(avdb.get("enabled"), default=False),
        "sync_enabled": _as_bool(avdb.get("sync_enabled"), default=False),
        "available": _as_bool(status.get("available"), default=False),
    }


def _persist_sources(
    sources: dict,
    *,
    avdb_changed: bool,
    avdb_status: dict | None = None,
) -> dict:
    previous_sources = copy.deepcopy(_saved_sources())
    config.replace_sources(sources)
    try:
        _refresh_runtime(avdb_changed=avdb_changed)
    except Exception as refresh_error:
        logger.exception("Source runtime refresh failed; rolling back source config")
        try:
            config.replace_sources(previous_sources)
        except Exception as rollback_error:
            raise RuntimeError(
                f"来源运行时刷新失败，且配置回滚失败: {rollback_error}"
            ) from rollback_error
        try:
            _refresh_runtime(avdb_changed=avdb_changed)
        except Exception:
            logger.exception("Failed to restore source runtime after config rollback")
        raise refresh_error
    return get_source_snapshot(avdb_status=avdb_status)


def _refresh_runtime(*, avdb_changed: bool) -> None:
    from sources import register_all_sources

    register_all_sources()
    if avdb_changed:
        from scheduler.tasks import configure_avdb_sync_job, scheduler

        if scheduler.running:
            configure_avdb_sync_job()


def _read_avdb_status() -> dict:
    try:
        return _status_dict(get_avdb_status())
    except Exception as exc:
        return {
            "available": False,
            "status": "unknown",
            "last_error": str(exc) or exc.__class__.__name__,
        }


def _status_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _payload_dict(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise SourceConfigError("请求内容必须是对象", status_code=400)
    return payload


def _torznab_kind(item: dict) -> str:
    return _text(item.get("kind")) or "torznab"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    return parsed.scheme.casefold() in {"http", "https"} and bool(hostname)


__all__ = [
    "LEGACY_TORZNAB_ID",
    "SourceConfigError",
    "get_source_snapshot",
    "create_source",
    "update_source",
    "delete_source",
    "source_runtime_name",
]
