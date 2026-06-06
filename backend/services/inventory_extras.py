"""Find Emby snapshot videos that JavInfo does not know about."""
from __future__ import annotations

import re
from pathlib import PurePath
from typing import Any

from database.snapshot import iter_snapshot_videos_by_actor
from modules.info_client import get_info_client


_CODE_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2,})[-_ ]?(\d{1,6})(?![A-Z0-9])", re.IGNORECASE)


def _normalize_code(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _canonical_code(prefix: str, digits: str) -> str:
    return f"{prefix.upper()}-{str(int(digits))}"


def _extract_code(row: dict[str, Any]) -> str | None:
    filename = str(row.get("filename") or "")
    filename_stem = PurePath(filename).stem if filename else ""
    text = " ".join(str(value or "") for value in (row.get("title"), filename_stem))
    match = _CODE_RE.search(text)
    if not match:
        return None
    return _canonical_code(match.group(1), match.group(2))


def _video_codes(items: list[dict[str, Any]]) -> set[str]:
    codes: set[str] = set()
    for item in items:
        for key in ("dvd_id", "content_id", "canonical_number", "canonical_code"):
            normalized = _normalize_code(item.get(key))
            if normalized:
                codes.add(normalized)
    return codes


def _row_payload(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "emby_item_id": row.get("emby_item_id"),
        "filename": row.get("filename") or row.get("title") or "",
        "reason": reason,
    }


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("emby_item_id") or row.get("filename") or row.get("title") or "").strip()
        if not key:
            key = str(id(row))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


async def _javinfo_actor_codes(info_client: Any, actor_id: int | None) -> set[str]:
    if actor_id is None:
        return set()
    try:
        result = await info_client.get_all_actress_videos(
            int(actor_id),
            include_supplement="1",
            cache_bypass=True,
        )
    except Exception:
        return set()
    items = result.get("data") if isinstance(result, dict) else []
    return _video_codes(items if isinstance(items, list) else [])


async def list_extras(
    snapshot_key: str,
    actor_id: int | None = None,
    limit: int = 200,
    info_client: Any | None = None,
) -> list[dict[str, Any]]:
    client = info_client or get_info_client()
    safe_limit = max(1, min(int(limit or 200), 1000))
    snapshot_limit = safe_limit if actor_id is not None else min(1000, safe_limit * 5)
    rows = _dedupe_rows(iter_snapshot_videos_by_actor(snapshot_key, actor_id, snapshot_limit))
    actor_codes = await _javinfo_actor_codes(client, actor_id)

    no_code: list[dict[str, Any]] = []
    candidates: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        code = _extract_code(row)
        if not code:
            no_code.append(_row_payload(row, "no_code"))
            continue
        if actor_codes and _normalize_code(code) in actor_codes:
            continue
        candidates.append((row, code))

    lookup_codes = list(dict.fromkeys(code for _row, code in candidates))
    found_codes: set[str] = set()
    if lookup_codes:
        try:
            found = await client.batch_lookup_by_dvd_id(lookup_codes)
        except Exception:
            found = {}
        if isinstance(found, dict):
            found_codes = {
                _normalize_code(key)
                for key, value in found.items()
                if isinstance(value, dict) and value
            }

    extras: list[dict[str, Any]] = []
    for row, code in candidates:
        if _normalize_code(code) not in found_codes:
            extras.append(_row_payload(row, "not_in_javinfo"))
    extras.extend(no_code)
    return extras[:safe_limit]
