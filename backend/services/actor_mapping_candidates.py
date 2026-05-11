"""Generate Emby actor -> JavInfo actress mapping candidates."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from database import get_latest_snapshot_key, get_snapshot_actors, list_actor_mappings, upsert_actor_mapping
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


def actor_mapping_confidence(emby_name: str, candidate: dict[str, Any]) -> float:
    source = _normalize_name(emby_name)
    names = [
        candidate.get("name_kanji"),
        candidate.get("name_romaji"),
        candidate.get("name_ja"),
        candidate.get("name_en"),
        candidate.get("name"),
    ]
    best = 0.0
    for name in names:
        target = _normalize_name(str(name or ""))
        if not source or not target:
            continue
        if source == target:
            score = 1.0
        elif source in target or target in source:
            score = 0.9
        else:
            score = SequenceMatcher(None, source, target).ratio()
        best = max(best, score)
    return round(best, 3)


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

    decisions = {
        str(row["emby_actor_id"]): row
        for row in list_actor_mappings(limit=100000)
        if row.get("status") == "confirmed" or (row.get("status") == "ignored" and row.get("javinfo_actress_id") is None)
    }
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
        scored = []
        for row in rows:
            actress_id = row.get("id")
            if not actress_id:
                continue
            confidence = actor_mapping_confidence(emby_actor_name, row)
            if confidence < min_confidence:
                continue
            scored.append((confidence, row))
        scored.sort(key=lambda item: (item[0], item[1].get("movie_count") or 0), reverse=True)

        for confidence, row in scored[:per_actor]:
            name = _candidate_name(row)
            mapping_id = upsert_actor_mapping(
                emby_actor_id=emby_actor_id,
                emby_actor_name=emby_actor_name,
                javinfo_actress_id=int(row["id"]),
                javinfo_actress_name=name,
                confidence=confidence,
                status="candidate",
                source="name_match",
            )
            created += 1
            candidates.append({
                "id": mapping_id,
                "emby_actor_id": emby_actor_id,
                "emby_actor_name": emby_actor_name,
                "javinfo_actress_id": int(row["id"]),
                "javinfo_actress_name": name,
                "confidence": confidence,
                "movie_count": row.get("movie_count", 0),
            })
        if checked >= limit:
            break

    return {
        "snapshot_key": snapshot_key,
        "checked": checked,
        "created": created,
        "candidates": candidates,
    }
