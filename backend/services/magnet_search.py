"""Shared magnet-source search, verification, ranking, and de-duplication."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from modules.code_matcher import code_matches_any
from services.secret_redactor import redact_attempt_rows, sanitize_source_item_uris
from services.video_variants import search_codes_for_item
from sources.registry import SourceRegistry


_MIN_REASONABLE_MBPS = 1.5
_MAX_REASONABLE_MBPS = 12.0
_MIN_REASONABLE_MB = 800.0
_MAX_REASONABLE_MB = 12.0 * 1024.0
_SOURCE_TEXT_FIELDS = (
    "magnet",
    "torrent_url",
    "download_url",
    "title",
    "name",
    "size",
    "quality",
    "resolution",
    "source",
    "info_hash",
)
_SOURCE_BOOL_FIELDS = ("hd", "subtitle")
_SOURCE_INT_FIELDS = ("seeders", "leechers", "peers")
_OPTIONAL_TEXT_FIELDS = frozenset({"quality", "resolution"})


def magnet_identity(item: dict) -> str:
    """Return a stable download identity, preferring hashes over full URIs."""
    info_hash = str(item.get("info_hash") or "").strip()
    if info_hash:
        return f"btih:{info_hash.casefold()}"

    uri = _download_uri(item)
    if not uri:
        return ""
    btih = _btih_from_uri(uri)
    if btih:
        return f"btih:{btih.casefold()}"
    return f"uri:{_normalized_uri(uri)}"


def magnet_score(
    item: dict,
    *,
    duration_seconds: float = 0,
    source_health: dict | None = None,
) -> dict:
    """Return the existing acquisition score and its named reason breakdown."""
    title = str(item.get("title") or "").lower()
    quality = str(item.get("quality") or "").lower()
    subtitle = bool(item.get("subtitle")) or any(
        token in title for token in ("字幕", "subtitle", "sub")
    )
    hd = (
        bool(item.get("hd"))
        or "1080" in title
        or "2160" in title
        or "4k" in title
        or "hd" in quality
    )
    resolution_rank = _resolution_rank(item)
    size_mb = _size_to_mb(item.get("size"))
    health = _source_health_score(item, source_health)
    fit = _size_fit(size_mb, duration_seconds)
    subtitle_score = 1 if subtitle else 0
    total = subtitle_score * 1000 + resolution_rank * 100 + health * 10 + fit
    return {
        "subtitle": subtitle_score,
        "hd": 1 if hd else 0,
        "resolution": resolution_rank,
        "size_mb": size_mb,
        "health": health,
        "size_fit": fit,
        "total": total,
    }


def canonicalize_source_item(item: dict) -> dict:
    """Keep only known acquisition fields with JSON-safe scalar values."""
    source = dict(item or {})
    row: dict[str, Any] = {}
    for key in _SOURCE_TEXT_FIELDS:
        if key not in source:
            continue
        value = source.get(key)
        if value is None and key in _OPTIONAL_TEXT_FIELDS:
            row[key] = None
        elif isinstance(value, str):
            row[key] = value
    for key in _SOURCE_BOOL_FIELDS:
        value = source.get(key)
        if isinstance(value, bool):
            row[key] = value
        elif isinstance(value, int) and value in {0, 1}:
            row[key] = bool(value)
    for key in _SOURCE_INT_FIELDS:
        value = source.get(key)
        if isinstance(value, bool):
            continue
        try:
            normalized = int(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if isinstance(value, float) and not value.is_integer():
            continue
        row[key] = normalized
    return row


async def search_magnets(
    keyword: str,
    source_names: list[str] | None = None,
) -> dict:
    """Search all or selected runtime sources, preserving partial successes."""
    return await _search_magnets(
        keyword,
        source_names=source_names,
        deduplicate=True,
    )


async def _search_magnets(
    keyword: str,
    *,
    source_names: list[str] | None,
    deduplicate: bool,
) -> dict:
    rows, attempts = await SourceRegistry.search_selected(keyword, source_names)
    attempts = redact_attempt_rows(attempts)
    safe_rows = []
    for item in rows:
        safe_item = sanitize_source_item_uris(dict(item))
        if safe_item is not None:
            safe_rows.append(canonicalize_source_item(safe_item))
    ranked = _ranked_entries(
        {"item": dict(item), "score": magnet_score(item), "verified": False}
        for item in safe_rows
    )
    if deduplicate:
        ranked = _dedupe_ranked(ranked)
    items = [dict(entry["item"]) for entry in ranked]
    errors = [attempt for attempt in attempts if not attempt.get("ok")]
    return {"items": items, "attempts": attempts, "errors": errors}


async def search_magnets_for_item(
    item: dict,
    source_names: list[str] | None = None,
) -> dict:
    """Search an item's ordered code aliases with candidate-compatible rules."""
    scored: list[dict] = []
    attempts: list[dict] = []

    for keyword in search_codes_for_item(item):
        batch = await _search_magnets(
            keyword,
            source_names=source_names,
            deduplicate=False,
        )
        attempts.extend(batch.get("attempts") or [])
        for row in batch.get("items") or []:
            if not _download_uri(row):
                continue
            verified = code_matches_any(
                keyword,
                [row.get("title"), row.get("name")],
            )
            scored.append(
                {
                    "item": dict(row),
                    "score": magnet_score(row),
                    "verified": verified,
                }
            )
        if any(entry["verified"] for entry in scored):
            break

    if any(entry["verified"] for entry in scored):
        scored = [entry for entry in scored if entry["verified"]]

    ranked = _dedupe_ranked(_ranked_entries(scored))
    items = [dict(entry["item"]) for entry in ranked]
    candidates = ranked[:5]
    best = None
    if candidates:
        best = dict(candidates[0]["item"])
        best["reason_breakdown"] = candidates[0]["score"]
    alternatives = _sanitize_alternatives(
        {
            "magnet": _download_uri(entry["item"]),
            "source": entry["item"].get("source") or entry["item"].get("name"),
            "title": entry["item"].get("title") or "",
            "score": entry["score"],
        }
        for entry in candidates
    )
    errors = [attempt for attempt in attempts if not attempt.get("ok")]
    return {
        "items": items,
        "attempts": attempts,
        "errors": errors,
        "best": best,
        "candidates": candidates,
        "alternatives": alternatives,
    }


def _ranked_entries(entries) -> list[dict]:
    return sorted(
        entries,
        key=lambda entry: (
            entry["score"]["total"],
            _seeders(entry["item"]),
        ),
        reverse=True,
    )


def _dedupe_ranked(entries: list[dict]) -> list[dict]:
    deduped = []
    seen: set[str] = set()
    for entry in entries:
        identity = magnet_identity(entry["item"])
        if identity and identity in seen:
            continue
        if identity:
            seen.add(identity)
        deduped.append(entry)
    return deduped


def _sanitize_alternatives(entries) -> list[dict]:
    alternatives = []
    seen: set[str] = set()
    for entry in entries:
        uri = _download_uri(entry)
        if not uri:
            continue
        identity = magnet_identity(entry)
        if identity in seen:
            continue
        seen.add(identity)
        alternatives.append(
            {
                "magnet": uri,
                "source": entry.get("source") or entry.get("name"),
                "title": entry.get("title") or "",
                "score": entry.get("score"),
            }
        )
    return alternatives[:5]


def _download_uri(item: dict) -> str:
    for key in ("magnet", "torrent_url", "download_url"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _btih_from_uri(uri: str) -> str:
    try:
        pairs = parse_qsl(urlsplit(uri).query, keep_blank_values=True)
    except ValueError:
        pairs = []
    for key, value in pairs:
        if key.casefold() != "xt":
            continue
        match = re.fullmatch(r"(?i)urn:btih:(.+)", value.strip())
        if match:
            return match.group(1).strip()
    return ""


def _normalized_uri(uri: str) -> str:
    text = str(uri or "").strip()
    try:
        parsed = urlsplit(text)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return text
    pairs.sort(key=lambda pair: (pair[0].casefold(), pair[1]))
    query = urlencode(pairs, doseq=True, quote_via=quote)
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path,
            query,
            parsed.fragment,
        )
    )


def _seeders(item: dict) -> int:
    try:
        return int(item.get("seeders") or 0)
    except (TypeError, ValueError):
        return 0


def _size_to_mb(value: str | None) -> float:
    text = str(value or "").strip().upper().replace(",", "")
    if not text:
        return 0
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB|MB|KB)?", text)
    if not match:
        return 0
    number = float(match.group(1))
    unit = match.group(2) or "MB"
    if unit == "TB":
        return number * 1024 * 1024
    if unit == "GB":
        return number * 1024
    if unit == "KB":
        return number / 1024
    return number


def _resolution_rank(item: dict) -> int:
    haystack = " ".join(
        str(item.get(key) or "").lower()
        for key in ("title", "resolution", "quality")
    )
    if "2160" in haystack or "4k" in haystack:
        return 1
    if "1080" in haystack:
        return 4
    if "720" in haystack:
        return 3
    return 2


def _size_fit(size_mb: float, duration_seconds: float) -> float:
    size_mb = float(size_mb or 0)
    if size_mb <= 0:
        return 0.5
    if duration_seconds and duration_seconds > 0:
        mbps = (size_mb * 8.0) / float(duration_seconds)
        if _MIN_REASONABLE_MBPS <= mbps <= _MAX_REASONABLE_MBPS:
            return 1.0
        if mbps < _MIN_REASONABLE_MBPS:
            return max(0.0, mbps / _MIN_REASONABLE_MBPS)
        return max(0.0, _MAX_REASONABLE_MBPS / mbps)
    if _MIN_REASONABLE_MB <= size_mb <= _MAX_REASONABLE_MB:
        return 1.0
    if size_mb < _MIN_REASONABLE_MB:
        return max(0.0, size_mb / _MIN_REASONABLE_MB)
    return max(0.0, _MAX_REASONABLE_MB / size_mb)


def _source_health_score(item: dict, source_health: dict | None) -> float:
    if not source_health:
        return 0.5
    source = str(item.get("source") or item.get("name") or "").strip()
    rate: Any = source_health.get(source)
    if rate is None:
        return 0.5
    try:
        return max(0.0, min(1.0, float(rate)))
    except (TypeError, ValueError):
        return 0.5
