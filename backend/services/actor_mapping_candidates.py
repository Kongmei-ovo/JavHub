"""Generate Emby actor -> JavInfo actress mapping candidates."""
from __future__ import annotations

import re
import json
from difflib import SequenceMatcher
from typing import Any

from config import config
from database import (
    confirm_actor_mapping,
    get_latest_snapshot_key,
    get_snapshot_actors,
    list_actor_mappings,
    update_actor_mapping_ai_review,
    upsert_actor_mapping,
)
from modules.info_client import get_info_client
from services.ai import get_ai_client


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
        name_confidence = score["confidence"]
        if name_confidence < min_confidence:
            continue
        scored.append({
            "row": row,
            "confidence": name_confidence,
            "name_confidence": name_confidence,
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
    _annotate_confidence(scored)
    return scored


def _candidate_avatar_url(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("image_url")
        or candidate.get("avatar_url")
        or candidate.get("javinfo_avatar_url")
        or candidate.get("portrait_url")
        or ""
    ).strip()


def _safe_movie_count(candidate: dict[str, Any]) -> int:
    try:
        return max(0, int(candidate.get("movie_count") or 0))
    except Exception:
        return 0


def _confidence_label(confidence: float, risk_flags: list[str] | None = None) -> str:
    risks = risk_flags or []
    if confidence >= 0.9 and not any("歧义" in risk or "分差" in risk for risk in risks):
        return "高置信"
    if confidence >= 0.75:
        return "中置信"
    return "低置信"


def _annotate_confidence(scored: list[dict[str, Any]]) -> None:
    if not scored:
        return
    total = len(scored)
    gap_threshold = config.actor_mapping_auto_confirm_gap
    top_gap = scored[0]["name_confidence"] - scored[1]["name_confidence"] if len(scored) > 1 else None
    for index, item in enumerate(scored):
        row = item["row"]
        name_score = float(item["name_confidence"])
        movie_count = _safe_movie_count(row)
        if movie_count >= 20:
            movie_score = 1.0
        elif movie_count >= 5:
            movie_score = 0.85
        elif movie_count > 0:
            movie_score = 0.7
        else:
            movie_score = 0.5

        if total == 1:
            uniqueness_score = 1.0
            gap_score = 1.0
        else:
            own_gap = top_gap if index == 0 else max(0.0, scored[index - 1]["name_confidence"] - name_score)
            gap_score = min(1.0, max(0.0, (own_gap or 0.0) / gap_threshold)) if gap_threshold else 1.0
            uniqueness_score = 0.95 if gap_score >= 1.0 else (0.65 if index == 0 else 0.55)

        confidence = round(min(1.0, (name_score * 0.78) + (movie_score * 0.07) + (uniqueness_score * 0.10) + (gap_score * 0.05)), 3)
        risk_flags: list[str] = []
        signals: list[str] = []
        if item["match_type"] == "exact":
            signals.append("名称精确一致")
        elif item["match_type"] == "contains":
            signals.append("名称存在包含关系")
            risk_flags.append("名称不是完全一致")
        else:
            signals.append("名称仅相似")
            risk_flags.append("名称仅相似")
        if total == 1:
            signals.append("候选唯一")
        elif index == 0 and top_gap is not None and top_gap < gap_threshold:
            risk_flags.append("候选分差小")
        if movie_count >= 20:
            signals.append("作品数充足")
        elif movie_count == 0:
            risk_flags.append("作品数未知")
        elif movie_count < 5:
            risk_flags.append("作品数偏少")
        if not _candidate_avatar_url(row):
            risk_flags.append("缺少头像")

        label = _confidence_label(confidence, risk_flags)
        item["confidence"] = confidence
        item["movie_count"] = movie_count
        item["javinfo_avatar_url"] = _candidate_avatar_url(row)
        item["confidence_label"] = label
        item["risk_flags"] = risk_flags
        item["confidence_breakdown"] = {
            "name_score": round(name_score, 3),
            "movie_score": round(movie_score, 3),
            "uniqueness_score": round(uniqueness_score, 3),
            "gap_score": round(gap_score, 3),
            "final_score": confidence,
            "candidate_count": total,
            "rank": index + 1,
            "top_gap": round(top_gap, 3) if top_gap is not None else None,
            "signals": signals,
        }


def mapping_candidate_from_row(row: dict[str, Any]) -> dict[str, Any]:
    confidence = round(float(row.get("confidence") or 0), 3)
    risk_flags = row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else []
    return {
        **row,
        "reason": row.get("source") or row.get("reason") or "",
        "movie_count": row.get("movie_count") or 0,
        "javinfo_avatar_url": row.get("javinfo_avatar_url") or "",
        "confidence": confidence,
        "confidence_breakdown": row.get("confidence_breakdown") if isinstance(row.get("confidence_breakdown"), dict) else {},
        "confidence_label": row.get("confidence_label") or _confidence_label(confidence, risk_flags),
        "risk_flags": risk_flags,
        "ai_decision": row.get("ai_decision") or "",
        "ai_confidence": row.get("ai_confidence"),
        "ai_reason": row.get("ai_reason") or "",
        "ai_model": row.get("ai_model") or "",
        "ai_reviewed_at": row.get("ai_reviewed_at") or "",
    }


def normalize_actor_mapping_search_candidate(emby_actor_id: str, emby_actor_name: str, item: dict[str, Any]) -> dict[str, Any]:
    payload = _candidate_payload(
        emby_actor_id,
        emby_actor_name,
        item,
        reason=_mapping_reason(item),
    )
    payload["source"] = payload["reason"]
    return payload


async def search_actor_mapping_candidates(
    emby_actor_id: str | int,
    emby_actor_name: str,
    q: str | None = None,
    limit: int = 10,
    min_confidence: float | None = None,
    info_client=None,
) -> dict[str, Any]:
    """Search JavInfo for one Emby actor and return normalized, scored candidates."""
    emby_actor_id = str(emby_actor_id or "")
    emby_actor_name = str(emby_actor_name or "").strip()
    query = str(q or emby_actor_name).strip()
    if not emby_actor_id or not emby_actor_name or not query:
        return {"data": [], "total": 0}

    min_confidence = min_confidence if min_confidence is not None else config.actor_mapping_candidate_min_confidence
    client = info_client or get_info_client()
    result = await client.list_actresses(q=query, page=1, page_size=max(limit * 2, 10))
    rows = result.get("data", []) if isinstance(result, dict) else []
    scored = _score_rows(emby_actor_name, rows, min_confidence=0.0)
    candidates = [normalize_actor_mapping_search_candidate(emby_actor_id, emby_actor_name, item) for item in scored]
    candidates = [candidate for candidate in candidates if float(candidate.get("confidence") or 0) >= min_confidence]
    return {"data": candidates[:limit], "total": len(candidates)}


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
        except Exception:
            return {}
    return data if isinstance(data, dict) else {}


def _ai_review_payload(emby_actor_name: str, candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "emby_actor_name": emby_actor_name,
        "javinfo_actress_name": candidate.get("javinfo_actress_name") or _candidate_name(candidate),
        "javinfo_actress_id": candidate.get("javinfo_actress_id") or candidate.get("id"),
        "movie_count": candidate.get("movie_count") or 0,
        "rule_confidence": candidate.get("confidence") or 0,
        "match_type": candidate.get("match_type") or candidate.get("source") or candidate.get("reason") or "",
        "risk_flags": candidate.get("risk_flags") or [],
        "signals": (candidate.get("confidence_breakdown") or {}).get("signals", []),
        "candidate_names": _candidate_names(candidate),
    }


async def review_actor_mapping_with_ai(
    emby_actor_id: str | int,
    emby_actor_name: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Use configured shared AI chat provider for text-only actor mapping review."""
    javinfo_id = candidate.get("javinfo_actress_id") or candidate.get("id")
    if not javinfo_id:
        raise ValueError("javinfo_actress_id is required")
    javinfo_name = candidate.get("javinfo_actress_name") or _candidate_name(candidate)
    payload_context = _ai_review_payload(str(emby_actor_name or ""), {**candidate, "javinfo_actress_name": javinfo_name})
    system_prompt = (
        "You help review whether an Emby actor and a JavInfo actress are the same person. "
        "Use only the provided text signals. Do not infer from images. "
        "Return strict JSON with keys decision, confidence, reason. "
        "decision must be one of same_person, different_person, uncertain. "
        "confidence must be a number from 0 to 1. reason must be concise Chinese."
    )
    user_prompt = json.dumps(payload_context, ensure_ascii=False, indent=2)
    response = await get_ai_client().chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        json_mode=True,
        temperature=0.1,
    )
    content = response.content
    parsed = _extract_json_object(content)
    decision = str(parsed.get("decision") or "uncertain").strip()
    if decision not in {"same_person", "different_person", "uncertain"}:
        decision = "uncertain"
    try:
        ai_confidence = max(0.0, min(float(parsed.get("confidence", 0)), 1.0))
    except Exception:
        ai_confidence = 0.0
    ai_reason = str(parsed.get("reason") or "").strip()[:500]
    if not ai_reason:
        ai_reason = "AI 未返回明确理由"

    mapping_id = update_actor_mapping_ai_review(
        emby_actor_id=emby_actor_id,
        javinfo_actress_id=int(javinfo_id),
        ai_decision=decision,
        ai_confidence=round(ai_confidence, 3),
        ai_reason=ai_reason,
        ai_model=response.model,
    )
    return {
        "id": mapping_id,
        "emby_actor_id": str(emby_actor_id),
        "javinfo_actress_id": int(javinfo_id),
        "ai_decision": decision,
        "ai_confidence": round(ai_confidence, 3),
        "ai_reason": ai_reason,
        "ai_model": response.model,
    }


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
        "movie_count": item.get("movie_count", _safe_movie_count(row)),
        "javinfo_avatar_url": item.get("javinfo_avatar_url", _candidate_avatar_url(row)),
        "confidence_breakdown": item.get("confidence_breakdown", {}),
        "confidence_label": item.get("confidence_label") or _confidence_label(item["confidence"], item.get("risk_flags", [])),
        "risk_flags": item.get("risk_flags", []),
    }
    if mapping_id is not None:
        payload["id"] = mapping_id
    return payload


def _is_auto_confirmable(scored: list[dict[str, Any]], auto_confirm_confidence: float, auto_confirm_gap: float) -> bool:
    if not scored:
        return False
    top = scored[0]
    top_name_confidence = top.get("name_confidence", top["confidence"])
    if not top["exact"] or top_name_confidence < auto_confirm_confidence:
        return False
    if len(scored) == 1:
        return True
    second_name_confidence = scored[1].get("name_confidence", scored[1]["confidence"])
    return top_name_confidence - second_name_confidence >= auto_confirm_gap


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
            reason = _mapping_reason(item)
            mapping_id = upsert_actor_mapping(
                emby_actor_id=emby_actor_id,
                emby_actor_name=emby_actor_name,
                javinfo_actress_id=int(row["id"]),
                javinfo_actress_name=_candidate_name(row),
                confidence=item["confidence"],
                status="candidate",
                source=reason,
                javinfo_avatar_url=item.get("javinfo_avatar_url"),
                movie_count=item.get("movie_count"),
                confidence_breakdown=item.get("confidence_breakdown"),
                confidence_label=item.get("confidence_label"),
                risk_flags=item.get("risk_flags"),
            )
            created += 1
            candidates.append(_candidate_payload(emby_actor_id, emby_actor_name, item, mapping_id, reason))
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
                        javinfo_avatar_url=item.get("javinfo_avatar_url"),
                        movie_count=item.get("movie_count"),
                        confidence_breakdown=item.get("confidence_breakdown"),
                        confidence_label=item.get("confidence_label"),
                        risk_flags=item.get("risk_flags"),
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
                        javinfo_avatar_url=item.get("javinfo_avatar_url"),
                        movie_count=item.get("movie_count"),
                        confidence_breakdown=item.get("confidence_breakdown"),
                        confidence_label=item.get("confidence_label"),
                        risk_flags=item.get("risk_flags"),
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
