from __future__ import annotations

import copy
import re
from collections import defaultdict
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any


BONUS_EVIDENCE_RE = re.compile(
    r"FANZA限定|数量限定|特典版|生写真|チェキ|パンティ|ランジェリー|写真セット|生ポラ",
    re.IGNORECASE,
)
FC2_RE = re.compile(r"(?i)\bFC2(?:[-_\s]*PPV)?[-_\s]*([0-9]{3,})\b")
FC2_NORMALIZED_RE = re.compile(r"^FC2(?:PPV)?([0-9]+)$", re.IGNORECASE)
CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)([A-Z]*)$")
ON_DEMAND_SUFFIXES = ("RDOD", "BOD", "DOD")
BONUS_SUFFIXES = ("BTK", "TK", "EC", "DL")
LOW_NUMBER_COLLISION_PREFIXES = {
    "DIC",
    "DOG",
    "ISD",
    "JKD",
    "JMD",
    "MAD",
    "PPD",
    "RPD",
    "SH",
    "SRD",
    "SS",
    "SSD",
}


def enrich_video_variants(
    items: list[dict[str, Any]],
    *,
    variant_mode: str = "grouped",
    include_explanations: bool = False,
) -> list[dict[str, Any]]:
    enriched = []
    for index, item in enumerate(items or []):
        row = _enrich_one(item, include_explanations=include_explanations)
        row["_variant_input_index"] = index
        enriched.append(row)
    if variant_mode != "grouped":
        return [_strip_internal_fields(item) for item in enriched]
    return _group_safe_variants(enriched)


def _enrich_one(item: dict[str, Any], *, include_explanations: bool) -> dict[str, Any]:
    row = copy.deepcopy(item)
    analysis = _analyze_item(row)
    labels: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []

    def add_label(
        key: str,
        label: str,
        short_label: str,
        *,
        source: str,
        confidence: str,
        meaning: str,
        evidence: str = "",
        raw: str = "",
    ) -> None:
        if any(existing["key"] == key for existing in labels):
            return
        labels.append(
            {
                "key": key,
                "label": label,
                "short_label": short_label,
                "source": source,
                "confidence": confidence,
            }
        )
        if include_explanations:
            explanations.append(
                {
                    "key": key,
                    "label": label,
                    "raw": raw or analysis["raw_code"],
                    "meaning": meaning,
                    "source": source,
                    "confidence": confidence,
                    "evidence": evidence,
                }
            )

    service = str(row.get("service_code") or "").strip().lower()
    if service == "digital" or analysis["content_id_padded"]:
        add_label(
            "digital",
            "数字版",
            "数字",
            source="service",
            confidence="high",
            meaning="DMM/FANZA 数字内容 ID，不等同传统商品番号",
            evidence="service_code=digital" if service == "digital" else "content_id 使用 DMM 补零格式",
        )
    if service == "rental" or "rental_4_prefix" in analysis["markers"]:
        add_label(
            "rental",
            "租赁版",
            "租赁",
            source="service",
            confidence="high",
            meaning="FANZA/DMM 租赁版条目",
            evidence="service_code=rental" if service == "rental" else "番号带 4 前缀",
        )
    if "bod_suffix" in analysis["markers"]:
        add_label(
            "bod",
            "BOD 蓝光按需",
            "BOD",
            source="official",
            confidence="high",
            meaning="Blu-ray Disc On Demand，FANZA 官方说明为 BD-R 高画质按需盘",
            evidence="FANZA 帮助中心说明 BOD 为 Blu-ray Disc On Demand",
        )
    if "dod_suffix" in analysis["markers"] or "rdod_suffix" in analysis["markers"]:
        add_label(
            "dod",
            "DOD 按需DVD",
            "DOD",
            source="official",
            confidence="high",
            meaning="DVD Disc On Demand，FANZA 官方说明为 DVD-R 按需盘",
            evidence="FANZA 帮助中心说明 DOD 为 DVD Disc On Demand",
        )
    if analysis["bonus_evidence"] and (
        "tk_prefix" in analysis["markers"]
        or any(marker in analysis["markers"] for marker in ("tk_suffix", "btk_suffix", "ec_suffix", "dl_suffix"))
    ):
        fanza = "FANZA限定" in analysis["title"]
        add_label(
            "fanza_bonus" if fanza else "bonus",
            "FANZA限定特典" if fanza else "特典版",
            "特典",
            source="title",
            confidence="medium",
            meaning="标题显示为 FANZA/数量限定或附带写真、チェキ、パンティ、ランジェリー等特典",
            evidence=analysis["bonus_evidence"],
        )

    row["canonical_code"] = analysis["canonical_code"]
    row["display_code"] = _display_code(row, analysis)
    row["variant_labels"] = labels
    row["variant_explanations"] = explanations if include_explanations else []
    row["variant_group_count"] = 1
    row["variant_group_items"] = []
    row["_variant_sort_rank"] = _variant_sort_rank(row, labels)
    row["_variant_groupable"] = _is_groupable(analysis)
    row["_variant_title_key"] = _title_key(row)
    return row


def _analyze_item(row: dict[str, Any]) -> dict[str, Any]:
    raw_code = _raw_code(row)
    content_norm = _normalize(row.get("content_id"))
    dvd_norm = _normalize(row.get("dvd_id"))
    title = str(row.get("title_ja") or row.get("title_en") or row.get("title") or "")
    bonus_evidence = _bonus_evidence(title)
    analysis = _analyze_code(raw_code, allow_title_tk=bool(bonus_evidence))
    analysis["raw_code"] = raw_code
    analysis["content_id_padded"] = bool(content_norm and not dvd_norm and "padded_digits" in analysis["markers"])
    analysis["title"] = title
    analysis["bonus_evidence"] = bonus_evidence
    return analysis


def _analyze_code(raw: Any, *, allow_title_tk: bool) -> dict[str, Any]:
    original = str(raw or "").strip()
    normalized = _normalize(original)
    markers: list[str] = []
    if not normalized:
        return _analysis(original, "", "", "", "", tuple(markers))

    if match := FC2_RE.search(original):
        digits = _trim_digits(match.group(1))
        return _analysis(original, "FC2PPV" + digits, "FC2-PPV-" + digits, "FC2PPV", digits, tuple(markers))
    if match := FC2_NORMALIZED_RE.match(normalized):
        digits = _trim_digits(match.group(1))
        return _analysis(original, "FC2PPV" + digits, "FC2-PPV-" + digits, "FC2PPV", digits, tuple(markers))

    working = normalized
    if allow_title_tk and working.startswith("TK") and _looks_like_wrapped_tk(working):
        markers.append("tk_prefix")
        working = working[2:]
    if working.startswith("4") and len(working) > 1 and working[1].isalpha():
        markers.append("rental_4_prefix")
        working = working[1:]

    for suffix in ON_DEMAND_SUFFIXES:
        if working.endswith(suffix) and len(working) > len(suffix):
            markers.append("rdod_suffix" if suffix == "RDOD" else f"{suffix.lower()}_suffix")
            working = working[: -len(suffix)]
            break
    for suffix in BONUS_SUFFIXES:
        if allow_title_tk and working.endswith(suffix) and len(working) > len(suffix):
            markers.append(f"{suffix.lower()}_suffix")
            working = working[: -len(suffix)]
            break

    if match := CODE_RE.match(working):
        prefix, raw_digits, extra = match.groups()
        digits = _trim_digits(raw_digits)
        if raw_digits.startswith("0") and len(raw_digits) > max(3, len(digits)):
            markers.append("padded_digits")
        canonical_norm = f"{prefix}{digits}{extra}"
        return _analysis(original, canonical_norm, _display_from_parts(prefix, digits, extra), prefix, digits, tuple(dict.fromkeys(markers)))

    return _analysis(original, working, original.upper(), "", "", tuple(dict.fromkeys(markers)))


def _analysis(raw: str, canonical_norm: str, canonical_code: str, prefix: str, digits: str, markers: tuple[str, ...]) -> dict[str, Any]:
    return {
        "raw": raw,
        "normalized": _normalize(raw),
        "canonical_norm": canonical_norm,
        "canonical_code": canonical_code,
        "prefix": prefix,
        "digits": digits,
        "markers": markers,
    }


def _looks_like_wrapped_tk(normalized: str) -> bool:
    stripped = normalized[2:]
    match = CODE_RE.match(stripped)
    if not match:
        return False
    return len(match.group(1)) >= 3


def _group_safe_variants(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    result: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        if not item.get("_variant_groupable"):
            result.append((_input_index(item), item))
            continue
        groups[str(item.get("canonical_code") or item.get("display_code") or "")].append(item)

    for group_items in groups.values():
        if len(group_items) == 1 or not _safe_group(group_items):
            result.extend((_input_index(item), item) for item in group_items)
            continue
        ordered = sorted(group_items, key=_sort_key)
        primary = copy.deepcopy(ordered[0])
        visible_items = [_strip_internal_fields(copy.deepcopy(item)) for item in ordered]
        primary["variant_group_count"] = len(visible_items)
        primary["variant_group_items"] = visible_items
        result.append((min(_input_index(item) for item in group_items), primary))
    return [_strip_internal_fields(item) for _, item in sorted(result, key=lambda entry: entry[0])]


def _safe_group(items: list[dict[str, Any]]) -> bool:
    titles = [str(item.get("_variant_title_key") or "") for item in items]
    non_empty_titles = [title for title in titles if title]
    if len(non_empty_titles) < 2:
        titles_match = True
    else:
        base = max(non_empty_titles, key=len)
        titles_match = all(_title_similarity(base, title) >= 0.56 for title in non_empty_titles)
    if not titles_match:
        return False

    dates = [_parse_release_date(item.get("release_date")) for item in items]
    dates = [value for value in dates if value]
    date_tolerance_days = 180 if any(_has_label(item, "rental") for item in items) else 45
    if len(dates) >= 2 and (max(dates) - min(dates)).days > date_tolerance_days:
        return False

    runtimes = [_runtime_minutes(item.get("runtime_mins")) for item in items]
    runtimes = [value for value in runtimes if value]
    if len(runtimes) >= 2:
        tolerance = max(3, round(max(runtimes) * 0.05))
        if max(runtimes) - min(runtimes) > tolerance:
            return False

    actor_sets = [_actor_keys(item) for item in items]
    actor_sets = [actors for actors in actor_sets if actors]
    if len(actor_sets) >= 2:
        base = max(actor_sets, key=len)
        for actors in actor_sets:
            overlap = len(base & actors)
            if overlap / max(1, min(len(base), len(actors))) < 0.8:
                return False
            if overlap / max(1, len(base | actors)) < 0.6:
                return False

    return True


def _is_groupable(analysis: dict[str, Any]) -> bool:
    prefix = str(analysis.get("prefix") or "")
    digits = str(analysis.get("digits") or "")
    if not analysis.get("canonical_code") or not prefix or not digits:
        return False
    numeric = int(digits) if digits.isdigit() else 0
    if prefix in LOW_NUMBER_COLLISION_PREFIXES or numeric < 100:
        return False
    return True


def _variant_sort_rank(row: dict[str, Any], labels: list[dict[str, Any]]) -> int:
    keys = {label["key"] for label in labels}
    service = str(row.get("service_code") or "").lower()
    if not keys and service == "mono":
        return 0
    if "digital" in keys:
        return 10
    if "rental" in keys:
        return 20
    if "bod" in keys or "dod" in keys:
        return 30
    if "fanza_bonus" in keys or "bonus" in keys:
        return 40
    return 50


def _has_label(item: dict[str, Any], key: str) -> bool:
    labels = item.get("variant_labels")
    return isinstance(labels, list) and any(label.get("key") == key for label in labels if isinstance(label, dict))


def _sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("_variant_sort_rank", 50),
        str(item.get("release_date") or ""),
        str(item.get("display_code") or item.get("dvd_id") or item.get("content_id") or ""),
    )


def _strip_internal_fields(item: dict[str, Any]) -> dict[str, Any]:
    for key in list(item):
        if key.startswith("_variant_"):
            item.pop(key, None)
    return item


def _input_index(item: dict[str, Any]) -> int:
    value = item.get("_variant_input_index")
    return value if isinstance(value, int) else 0


def _raw_code(row: dict[str, Any]) -> str:
    return str(row.get("dvd_id") or row.get("content_id") or row.get("display_code") or "").strip()


def _display_code(row: dict[str, Any], analysis: dict[str, Any]) -> str:
    dvd_id = str(row.get("dvd_id") or "").strip()
    if dvd_id:
        return dvd_id
    return str(analysis.get("canonical_code") or row.get("content_id") or "").strip()


def _normalize(value: Any) -> str:
    return "".join(ch.upper() for ch in str(value or "").strip() if ch.isalnum())


def _trim_digits(value: Any) -> str:
    trimmed = str(value or "").lstrip("0")
    return trimmed or "0"


def _display_from_parts(prefix: str, digits: str, extra: str = "") -> str:
    if not prefix or not digits:
        return ""
    return f"{prefix}-{digits}{extra}"


def _bonus_evidence(title: str) -> str:
    matches = list(dict.fromkeys(match.group(0) for match in BONUS_EVIDENCE_RE.finditer(title or "")))
    return " / ".join(matches[:4])


def _title_key(row: dict[str, Any]) -> str:
    title = str(row.get("title_ja") or row.get("title_en") or row.get("title") or "")
    title = re.sub(r"【[^】]*(?:FANZA限定|数量限定|特典版)[^】]*】", "", title, flags=re.IGNORECASE)
    title = re.sub(r"（?(?:BOD|DOD|RDOD|ブルーレイディスク)）?", "", title, flags=re.IGNORECASE)
    title = re.sub(r"(?:生写真|チェキ|パンティ|ランジェリー|写真セット|生ポラ).*$", "", title, flags=re.IGNORECASE)
    return re.sub(r"\W+", "", title).lower()


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 1.0
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b))
    return SequenceMatcher(None, a, b).ratio()


def _parse_release_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _runtime_minutes(value: Any) -> int | None:
    try:
        minutes = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return minutes if minutes > 0 else None


def _actor_keys(item: dict[str, Any]) -> set[str]:
    keys: set[str] = set()

    def add(value: Any) -> None:
        text = re.sub(r"\W+", "", str(value or "").lower())
        if text:
            keys.add(text)

    for field in ("actresses", "actors"):
        values = item.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                actor_id = value.get("id") or value.get("actress_id")
                if actor_id:
                    keys.add(f"id:{actor_id}")
                    continue
                for name_field in ("name_kanji", "name_romaji", "name_ja", "name_en", "name"):
                    if value.get(name_field):
                        add(value[name_field])
                        break
            else:
                add(value)

    for field in ("actress_name", "actress_names", "actor_name", "actor_names"):
        value = item.get(field)
        if isinstance(value, list):
            for entry in value:
                add(entry)
        else:
            add(value)

    return keys
