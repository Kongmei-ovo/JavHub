"""Generate Emby actor -> JavInfo actress mapping candidates."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from config import config
from database import (
    confirm_actor_mapping,
    get_latest_snapshot_key,
    get_snapshot_actors,
    list_actor_mappings,
    upsert_actor_mapping,
)
from modules.info_client import get_info_client


def _normalize_name(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s._・·,，。()（）\[\]【】\-]+", "", text)
    return text


def _candidate_name(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("name_kanji")
        or candidate.get("name_romaji")
        or candidate.get("name_ja")
        or candidate.get("name_en")
        or candidate.get("name")
        or ""
    ).strip()


def _candidate_names(candidate: dict[str, Any]) -> list[str]:
    return [
        str(candidate.get("name_kanji") or ""),
        str(candidate.get("name_romaji") or ""),
        str(candidate.get("name_ja") or ""),
        str(candidate.get("name_en") or ""),
        str(candidate.get("name") or ""),
    ]


def score_actor_mapping_candidate(emby_name: str, candidate: dict[str, Any]) -> dict[str, Any]:
    source = _normalize_name(emby_name)
    best = 0.0
    match_type = "none"
    exact = False
    for name in _candidate_names(candidate):
        target = _normalize_name(name)
        if not source or not target:
            continue
        if source == target:
            score = 1.0
            current_type = "exact"
        elif source in target or target in source:
            score = 0.9
            current_type = "contains"
        else:
            score = SequenceMatcher(None, source, target).ratio()
            current_type = "similar"
        if score > best:
            best = score
            match_type = current_type
            exact = current_type == "exact"
        elif score == best and current_type == "exact":
            match_type = "exact"
            exact = True
    return {
        "confidence": round(best, 3),
        "match_type": match_type,
        "exact": exact,
    }


def actor_mapping_confidence(emby_name: str, candidate: dict[str, Any]) -> float:
    best = score_actor_mapping_candidate(emby_name, candidate)["confidence"]
    return round(best, 3)


def _existing_actor_mapping_state() -> tuple[set[str], set[tuple[str, int]]]:
    decided_actor_ids = set()
    ignored_pairs = set()
    for row in list_actor_mappings(limit=100000):
        emby_actor_id = str(row.get("emby_actor_id") or "")
        status = row.get("status")
        javinfo_actress_id = row.get("javinfo_actress_id")
        if status == "confirmed" or (status == "ignored" and javinfo_actress_id is None):
            decided_actor_ids.add(emby_actor_id)
        if status == "ignored" and javinfo_actress_id is not None:
            try:
                ignored_pairs.add((emby_actor_id, int(javinfo_actress_id)))
            except Exception:
                continue
    return decided_actor_ids, ignored_pairs


def _score_rows(
    emby_actor_name: str,
    rows: list[dict[str, Any]],
    min_confidence: float,
) -> list[dict[str, Any]]:
    scored = []
    for row in rows:
        actress_id = row.get("id")
        if not actress_id:
            continue
        score = score_actor_mapping_candidate(emby_actor_name, row)
        confidence = score["confidence"]
        if confidence < min_confidence:
            continue
        scored.append({
            "row": row,
            "confidence": confidence,
            "match_type": score["match_type"],
            "exact": score["exact"],
        })
    scored.sort(
        key=lambda item: (
            item["confidence"],
            1 if item["exact"] else 0,
            item["row"].get("movie_count") or 0,
        ),
        reverse=True,
    )
    return scored


def _mapping_reason(
    item: dict[str, Any],
    top_gap: float | None = None,
    auto_confirm: bool = False,
    auto_confirm_gap: float | None = None,
) -> str:
    if auto_confirm:
        return "auto_confirmed_exact_unique"
    gap_threshold = auto_confirm_gap if auto_confirm_gap is not None else config.actor_mapping_auto_confirm_gap
    if item.get("exact") and top_gap is not None and top_gap < gap_threshold:
        return "exact_ambiguous"
    if item.get("match_type") == "exact":
        return "exact_review"
    if item.get("match_type") == "contains":
        return "contains_match"
    return "similar_match"


def _candidate_payload(
    emby_actor_id: str,
    emby_actor_name: str,
    item: dict[str, Any],
    mapping_id: int | None = None,
    reason: str = "",
) -> dict[str, Any]:
    row = item["row"]
    payload = {
        "emby_actor_id": emby_actor_id,
        "emby_actor_name": emby_actor_name,
        "javinfo_actress_id": int(row["id"]),
        "javinfo_actress_name": _candidate_name(row),
        "confidence": item["confidence"],
        "match_type": item["match_type"],
        "exact": item["exact"],
        "reason": reason,
        "movie_count": row.get("movie_count", 0),
    }
    if mapping_id is not None:
        payload["id"] = mapping_id
    return payload


def _is_auto_confirmable(scored: list[dict[str, Any]], auto_confirm_confidence: float, auto_confirm_gap: float) -> bool:
    if not scored:
        return False
    top = scored[0]
    if not top["exact"] or top["confidence"] < auto_confirm_confidence:
        return False
    if len(scored) == 1:
        return True
    return top["confidence"] - scored[1]["confidence"] >= auto_confirm_gap


async def generate_actor_mapping_candidates(
    search: str | None = None,
    limit: int = 50,
    per_actor: int = 3,
    min_confidence: float = 0.55,
    info_client=None,
) -> dict[str, Any]:
    """Search JavInfo for unmapped Emby actors and persist candidate mappings."""
    snapshot_key = get_latest_snapshot_key()
    if not snapshot_key:
        return {"snapshot_key": None, "checked": 0, "created": 0, "candidates": []}

    decisions, ignored_pairs = _existing_actor_mapping_state()
    actors = get_snapshot_actors(snapshot_key, search=search, page_size=100000).get("data", [])
    client = info_client or get_info_client()
    checked = 0
    created = 0
    candidates: list[dict[str, Any]] = []

    for actor in actors:
        emby_actor_id = str(actor.get("actress_id") or "")
        emby_actor_name = str(actor.get("actress_name") or "").strip()
        if not emby_actor_id or not emby_actor_name or emby_actor_id in decisions:
            continue
        checked += 1

        result = await client.list_actresses(q=emby_actor_name, page=1, page_size=max(per_actor * 3, 10))
        rows = result.get("data", []) if isinstance(result, dict) else []
        scored = [
            item for item in _score_rows(emby_actor_name, rows, min_confidence)
            if (emby_actor_id, int(item["row"]["id"])) not in ignored_pairs
        ]

        for item in scored[:per_actor]:
            row = item["row"]
            mapping_id = upsert_actor_mapping(
                emby_actor_id=emby_actor_id,
                emby_actor_name=emby_actor_name,
                javinfo_actress_id=int(row["id"]),
                javinfo_actress_name=_candidate_name(row),
                confidence=item["confidence"],
                status="candidate",
                source="name_match",
            )
            created += 1
            candidates.append(_candidate_payload(emby_actor_id, emby_actor_name, item, mapping_id, _mapping_reason(item)))
        if checked >= limit:
            break

    return {
        "snapshot_key": snapshot_key,
        "checked": checked,
        "created": created,
        "candidates": candidates,
    }


async def auto_match_actor_mappings(
    search: str | None = None,
    limit: int = 100000,
    dry_run: bool = False,
    snapshot_key: str | None = None,
    per_actor: int | None = None,
    min_confidence: float | None = None,
    auto_confirm_confidence: float | None = None,
    auto_confirm_gap: float | None = None,
    info_client=None,
) -> dict[str, Any]:
    """Generate mapping candidates and conservatively confirm exact unique matches."""
    snapshot_key = snapshot_key or get_latest_snapshot_key()
    if not snapshot_key:
        return {
            "snapshot_key": None,
            "dry_run": dry_run,
            "checked": 0,
            "auto_confirmed": 0,
            "candidates_created": 0,
            "ambiguous": 0,
            "skipped": 0,
            "errors": [],
            "candidates": [],
            "confirmed": [],
        }

    per_actor = per_actor or config.actor_mapping_candidate_per_actor
    min_confidence = min_confidence if min_confidence is not None else config.actor_mapping_candidate_min_confidence
    auto_confirm_confidence = (
        auto_confirm_confidence
        if auto_confirm_confidence is not None
        else config.actor_mapping_auto_confirm_confidence
    )
    auto_confirm_gap = auto_confirm_gap if auto_confirm_gap is not None else config.actor_mapping_auto_confirm_gap
    decisions, ignored_pairs = _existing_actor_mapping_state()
    actors = get_snapshot_actors(snapshot_key, search=search, page_size=100000).get("data", [])
    client = info_client or get_info_client()

    checked = 0
    auto_confirmed = 0
    candidates_created = 0
    ambiguous = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    confirmed: list[dict[str, Any]] = []

    for actor in actors:
        emby_actor_id = str(actor.get("actress_id") or "")
        emby_actor_name = str(actor.get("actress_name") or "").strip()
        if not emby_actor_id or not emby_actor_name:
            skipped += 1
            continue
        if emby_actor_id in decisions:
            skipped += 1
            continue
        if checked >= limit:
            break

        checked += 1
        try:
            result = await client.list_actresses(q=emby_actor_name, page=1, page_size=max(per_actor * 3, 10))
        except Exception as exc:
            errors.append({
                "emby_actor_id": emby_actor_id,
                "emby_actor_name": emby_actor_name,
                "error": str(exc),
            })
            continue

        rows = result.get("data", []) if isinstance(result, dict) else []
        scored = [
            item for item in _score_rows(emby_actor_name, rows, min_confidence)
            if (emby_actor_id, int(item["row"]["id"])) not in ignored_pairs
        ]
        if not scored:
            skipped += 1
            continue

        top_gap = scored[0]["confidence"] - scored[1]["confidence"] if len(scored) > 1 else None
        should_confirm = _is_auto_confirmable(scored, auto_confirm_confidence, auto_confirm_gap)
        if not should_confirm and scored[0]["exact"]:
            ambiguous += 1

        items_to_persist = scored[:1] if should_confirm else scored[:per_actor]
        for index, item in enumerate(items_to_persist):
            is_auto_confirm = index == 0 and should_confirm
            reason = _mapping_reason(
                item,
                top_gap=top_gap,
                auto_confirm=is_auto_confirm,
                auto_confirm_gap=auto_confirm_gap,
            )
            mapping_id = None
            if not dry_run:
                row = item["row"]
                if is_auto_confirm:
                    mapping_id = confirm_actor_mapping(
                        emby_actor_id=emby_actor_id,
                        emby_actor_name=emby_actor_name,
                        javinfo_actress_id=int(row["id"]),
                        javinfo_actress_name=_candidate_name(row),
                        confidence=item["confidence"],
                        source="auto_match",
                    )
                else:
                    mapping_id = upsert_actor_mapping(
                        emby_actor_id=emby_actor_id,
                        emby_actor_name=emby_actor_name,
                        javinfo_actress_id=int(row["id"]),
                        javinfo_actress_name=_candidate_name(row),
                        confidence=item["confidence"],
                        status="candidate",
                        source=reason,
                    )
            payload = _candidate_payload(emby_actor_id, emby_actor_name, item, mapping_id, reason)
            if is_auto_confirm:
                auto_confirmed += 1
                confirmed.append(payload)
            else:
                candidates_created += 1
                candidates.append(payload)

    return {
        "snapshot_key": snapshot_key,
        "dry_run": dry_run,
        "checked": checked,
        "auto_confirmed": auto_confirmed,
        "candidates_created": candidates_created,
        "ambiguous": ambiguous,
        "skipped": skipped,
        "errors": errors,
        "candidates": candidates,
        "confirmed": confirmed,
    }
