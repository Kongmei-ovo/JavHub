from __future__ import annotations

import copy
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any


BONUS_EVIDENCE_RE = re.compile(
    r"FANZA限定|数量限定|特典版|生写真|チェキ|パンティ|ランジェリー|写真セット|生ポラ",
    re.IGNORECASE,
)
FC2_RE = re.compile(r"(?i)\bFC2(?:[-_\s]*PPV)?[-_\s]*([0-9]{3,})\b")
FC2_NORMALIZED_RE = re.compile(r"^FC2(?:PPV)?([0-9]+)$", re.IGNORECASE)
CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)([A-Z]*)$")
ALNUM_CODE_RE = re.compile(r"^([0-9]*[A-Z][A-Z0-9]*?)([0-9]+)([A-Z]*)$")
# DMM "domestic" content_ids prefix the real code with a maker-bucket marker like
# `h_706naac00047b` (== NAAC-047B) or `h_1240sw00789` (== SW-789). Strip the
# prefix BEFORE the standard code analyzer so the canonical code matches the
# unprefixed FANZA/r18 form and variant grouping works across origins.
DOMESTIC_BUCKET_RE = re.compile(r"^H[0-9]{2,5}([A-Z][A-Z0-9]*[0-9][A-Z0-9]*)$")
BLURAY_BD_INFIX_RE = re.compile(r"^([A-Z]{2,})BD([0-9]+[A-Z]*)$")
BLURAY_B_PREFIX_RE = re.compile(r"^(PRBY)B([0-9]+[A-Z]*)$")
BLURAY_B_SUFFIX_RE = re.compile(r"^([A-Z]{2,})([0-9]+)B$")
ON_DEMAND_SUFFIXES = ("RDOD", "BOD", "DOD")
# Media-format suffix that DMM/FANZA tacks onto an otherwise identical code so
# the digital storefront can distinguish the physical disc package from the
# stream. The base code (without the suffix) is the canonical work id; the
# variant_labels machinery still surfaces "DVD 版"/"BD 版" through the existing
# label flow. We strip these unconditionally because DVD/BD is never the tail
# of a real upstream prefix.
MEDIA_SUFFIXES = ("DVD", "BD")
# Bonus-edition suffixes — Tower Records (TK/TKT/TKTB), HMV (HM), Amazon (AM),
# Tsutaya (TS), Rakuten (RK) and the legacy 数量限定/特典版 DP/SP markers all
# encode "same work, different store-exclusive bonus" and merge into the base
# code only when the title carries clear bonus evidence (FANZA限定/数量限定/
# チェキ/パンティ/...). Longer suffixes come first so the strip matches
# greedily — TKTB must beat TKT, BTK must beat TK.
BONUS_SUFFIXES = (
    "TKTB",
    "BTK",
    "TKT",
    "TK",
    "HM",
    "AM",
    "TS",
    "RK",
    "DP",
    "SP",
    "EC",
    "DL",
)
BLURAY_B_SUFFIX_PREFIXES = {"AP", "GTRP", "NAAC"}
BLURAY_BD_INFIX_PREFIXES = {"SSHN", "STAR"}
BLURAY_MARKERS = {
    "leading_9_bluray_prefix",
    "bluray_bd_infix",
    "bluray_b_prefix",
    "bluray_b_suffix",
}
RENTAL_R_STRIPPABLE_PREFIXES = {"DANDY", "NHDTA", "SSHN", "STAR", "STARS"}
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


# Service codes that are not movies at all (FANZA ebooks such as 月刊FANZA /
# 月刊SOD carry garbage dvd_ids like "2-020" and pollute filmographies, variant
# grouping and the Emby-compare pipeline).
NON_MOVIE_SERVICE_CODES = {"ebook"}


def is_non_movie_item(item: dict[str, Any]) -> bool:
    return str(item.get("service_code") or "").strip().lower() in NON_MOVIE_SERVICE_CODES


def filter_movie_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Drop non-movie rows (ebooks etc.) from a video list."""
    return [item for item in (items or []) if not is_non_movie_item(item)]


def search_codes_for_item(item: dict[str, Any]) -> list[str]:
    """Ordered keyword aliases for magnet/torrent search.

    The raw dvd_id/content_id of a variant row is often unsearchable
    (``4JUMS039`` rental prefix, ``h_706gtrp00004b`` bucket cid), and the
    de-padded canonical (``JUMS-39``) doesn't match scene naming either.
    Resources are conventionally named with the zero-padded display form
    (``JUMS-039``), so that goes first; raw identifiers come last as a
    fallback. All values are de-duplicated on their alphanumeric form.
    """
    row = dict(item or {})
    analysis = _analyze_item(row)
    codes: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip()
        normalized = _normalize(text)
        if not text or not normalized or normalized in seen:
            return
        seen.add(normalized)
        codes.append(text)

    prefix = str(analysis.get("prefix") or "")
    digits = str(analysis.get("digits") or "")
    if prefix == "FC2PPV" and digits:
        add(f"FC2-PPV-{digits}")
        add(f"FC2-{digits}")
    elif prefix and digits:
        extra = ""
        canonical_norm = str(analysis.get("canonical_norm") or "")
        if canonical_norm.startswith(prefix + digits):
            extra = canonical_norm[len(prefix) + len(digits):]
        padded = digits.zfill(3) if len(digits) < 3 else digits
        add(f"{prefix}-{padded}{extra}")
        add(f"{prefix}-{digits}{extra}")
        if extra:
            # The edition letter (e.g. GTRP-004B) often isn't in release names.
            add(f"{prefix}-{padded}")
    else:
        add(analysis.get("canonical_code"))
    add(row.get("dvd_id"))
    add(row.get("content_id"))
    return codes


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
    if service == "rental" or any(
        marker in analysis["markers"]
        for marker in ("rental_4_prefix", "rental_r_prefix", "h_bucket_rental_suffix")
    ):
        add_label(
            "rental",
            "租赁版",
            "租赁",
            source="service",
            confidence="high",
            meaning="FANZA/DMM 租赁版条目",
            evidence="service_code=rental" if service == "rental" else "番号包含租赁服务标记",
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
    if any(marker in analysis["markers"] for marker in BLURAY_MARKERS) or "bd_media_suffix" in analysis["markers"]:
        add_label(
            "blu_ray",
            "蓝光版",
            "蓝光",
            source="code",
            confidence="medium",
            meaning="番号包含常见 Blu-ray 版本标记，和基础番号归为同一作品的不同介质版本",
            evidence=", ".join(marker for marker in analysis["markers"] if marker in BLURAY_MARKERS or marker == "bd_media_suffix"),
        )
    if "dvd_media_suffix" in analysis["markers"]:
        add_label(
            "dvd",
            "DVD 版",
            "DVD",
            source="code",
            confidence="medium",
            meaning="番号末尾的 DVD 标记表示物理 DVD 介质版本，与基础番号合并为同一作品的不同介质版本",
            evidence="番号含 DVD 介质后缀",
        )
    # Store-exclusive bonus markers (Tower Records 限定/特典 etc.). Only label
    # them when the title carries bonus evidence so the chip reads consistently
    # with the existing "bonus"/"fanza_bonus" labels.
    store_marker_to_label = {
        "tkt_suffix": ("tower_bonus", "Tower 特典", "TKT"),
        "tktb_suffix": ("tower_bonus", "Tower 特典", "TKTB"),
        "tk_suffix": ("tower_bonus", "Tower 特典", "TK"),
        "btk_suffix": ("tower_bonus", "Tower 特典", "BTK"),
        "hm_suffix": ("hmv_bonus", "HMV 特典", "HMV"),
        "am_suffix": ("amazon_bonus", "Amazon 特典", "AMZN"),
        "ts_suffix": ("tsutaya_bonus", "Tsutaya 特典", "TSU"),
        "rk_suffix": ("rakuten_bonus", "Rakuten 特典", "楽天"),
        "dp_suffix": ("deluxe_pack", "豪华套装", "DP"),
        "sp_suffix": ("special_edition", "特别版", "SP"),
    }
    if analysis["bonus_evidence"]:
        for marker, (key, label, short) in store_marker_to_label.items():
            if marker not in analysis["markers"]:
                continue
            add_label(
                key,
                label,
                short,
                source="code",
                confidence="medium",
                meaning="番号尾部包含店铺限定/豪华套装等特典标记，和基础番号合并为同一作品的不同特典版本",
                evidence=marker,
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
    row["_variant_markers"] = analysis["markers"]
    return row


def _analyze_item(row: dict[str, Any]) -> dict[str, Any]:
    raw_code = _raw_code(row)
    content_norm = _normalize(row.get("content_id"))
    dvd_norm = _normalize(row.get("dvd_id"))
    title = str(row.get("title_ja") or row.get("title_en") or row.get("title") or "")
    bonus_evidence = _bonus_evidence(title)
    service = str(row.get("service_code") or "").strip().lower()
    raw_is_content_id = bool(content_norm and _normalize(raw_code) == content_norm)
    analysis = _analyze_code(
        raw_code,
        allow_title_tk=bool(bonus_evidence),
        allow_rental_r_prefix=service == "rental",
        allow_service_digit_prefix=service == "rental" or (service == "digital" and raw_is_content_id),
        allow_leading_9_bluray=True,
        allow_bluray_markers=True,
    )
    if service == "digital" and content_norm:
        content_analysis = _analyze_code(
            row.get("content_id"),
            allow_title_tk=bool(bonus_evidence),
            allow_service_digit_prefix=True,
            allow_bluray_markers=True,
        )
        if _should_prefer_digital_content_id(analysis, content_analysis, dvd_norm):
            content_analysis["markers"] = tuple(
                dict.fromkeys((*content_analysis["markers"], "digital_content_id_source"))
            )
            analysis = content_analysis
    analysis["raw_code"] = raw_code
    analysis["content_id_padded"] = bool(content_norm and not dvd_norm and "padded_digits" in analysis["markers"])
    analysis["title"] = title
    analysis["bonus_evidence"] = bonus_evidence
    return analysis


def _should_prefer_digital_content_id(
    raw_analysis: dict[str, Any],
    content_analysis: dict[str, Any],
    dvd_norm: str,
) -> bool:
    if not dvd_norm:
        return False
    if not _is_groupable(content_analysis):
        return False
    if not any(marker in content_analysis["markers"] for marker in ("padded_digits", "dmm_service_digit_prefix")):
        return False
    if not _is_groupable(raw_analysis):
        return True
    return str(raw_analysis.get("canonical_norm") or "") != str(content_analysis.get("canonical_norm") or "")


def _analyze_code(
    raw: Any,
    *,
    allow_title_tk: bool,
    allow_rental_r_prefix: bool = False,
    allow_service_digit_prefix: bool = False,
    allow_leading_9_bluray: bool = False,
    allow_bluray_markers: bool = False,
) -> dict[str, Any]:
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
    if match := DOMESTIC_BUCKET_RE.match(working):
        # h_706naac00047b → NAAC00047B. The bucket digits are routing metadata,
        # not part of the code; later edition-marker rules may still fold the
        # remaining suffix (for example Blu-ray B) into the base code.
        markers.append("h_bucket_prefix")
        working = match.group(1)
        if working.endswith("R") and _matches_parseable_code(working[:-1]):
            markers.append("h_bucket_rental_suffix")
            working = working[:-1]
    if allow_title_tk and working.startswith("TK") and _looks_like_wrapped_tk(working):
        markers.append("tk_prefix")
        working = working[2:]
    if allow_service_digit_prefix:
        digit_stripped = _strip_leading_service_digit(working)
        if digit_stripped:
            markers.append("dmm_service_digit_prefix")
            working = digit_stripped
    elif working.startswith("4") and len(working) > 1 and working[1].isalpha():
        markers.append("rental_4_prefix")
        working = working[1:]
    if allow_rental_r_prefix:
        rental_stripped = _strip_leading_rental_r(working)
        if rental_stripped:
            markers.append("rental_r_prefix")
            working = rental_stripped
    if allow_leading_9_bluray:
        bluray_stripped = _strip_leading_9_bluray(working)
        if bluray_stripped:
            markers.append("leading_9_bluray_prefix")
            working = bluray_stripped
    if allow_bluray_markers:
        bluray_stripped, marker = _strip_bluray_marker(working)
        if bluray_stripped:
            markers.append(marker)
            working = bluray_stripped

    for suffix in ON_DEMAND_SUFFIXES:
        if working.endswith(suffix) and len(working) > len(suffix):
            markers.append("rdod_suffix" if suffix == "RDOD" else f"{suffix.lower()}_suffix")
            working = working[: -len(suffix)]
            break
    # Peel a trailing media suffix (DVD/BD) BEFORE bonus stripping so that
    # NACT-138TKTDVD / NACT-138TKTBDVD reduce to NACT-138TKT / NACT-138TKTB
    # first, then the next BONUS_SUFFIXES sweep collapses the bonus marker.
    # The peel only fires when the remainder still parses as a real code so
    # we never butcher prefixes that genuinely end in DVD/BD.
    media_suffix = _strip_trailing_media_suffix(working)
    if media_suffix:
        marker, working = media_suffix
        markers.append(marker)
    for suffix in BONUS_SUFFIXES:
        if allow_title_tk and working.endswith(suffix) and len(working) > len(suffix):
            # Guard the minimum length so trimming the bonus marker still
            # leaves at least 3 digits' worth of code (prefix letters + digits).
            if len(working) - len(suffix) < 3:
                continue
            markers.append(f"{suffix.lower()}_suffix")
            working = working[: -len(suffix)]
            break
    # Pick up media suffixes that hid behind a bonus marker (e.g. some bonus
    # codes are followed by another DVD/BD tag like NACT-138BTKDVD).
    media_suffix = _strip_trailing_media_suffix(working)
    if media_suffix:
        marker, working = media_suffix
        markers.append(marker)

    if match := CODE_RE.match(working):
        prefix, raw_digits, extra = match.groups()
        digits = _trim_digits(raw_digits)
        if raw_digits.startswith("0") and len(raw_digits) > max(3, len(digits)):
            markers.append("padded_digits")
        canonical_norm = f"{prefix}{digits}{extra}"
        return _analysis(original, canonical_norm, _display_from_parts(prefix, digits, extra), prefix, digits, tuple(dict.fromkeys(markers)))

    if match := ALNUM_CODE_RE.match(working):
        prefix, raw_digits, extra = match.groups()
        digits = _trim_digits(raw_digits)
        if raw_digits.startswith("0") and len(raw_digits) > max(3, len(digits)):
            markers.append("padded_digits")
        canonical_norm = f"{prefix}{digits}{extra}"
        return _analysis(original, canonical_norm, _display_from_parts(prefix, digits, extra), prefix, digits, tuple(dict.fromkeys(markers)))

    return _analysis(original, working, original.upper(), "", "", tuple(dict.fromkeys(markers)))


def _strip_trailing_media_suffix(working: str) -> tuple[str, str] | None:
    """Peel a trailing DVD/BD media suffix if doing so still leaves a parseable
    code. Returns (marker_name, stripped_working) or None when no media suffix
    applies. Done as a helper because _analyze_code calls it twice — once
    before the bonus sweep and once after, so a layered XXXX-123 TKT DVD
    pattern collapses both ways."""
    for suffix in MEDIA_SUFFIXES:
        if not working.endswith(suffix) or len(working) <= len(suffix):
            continue
        candidate = working[: -len(suffix)]
        # Only commit the strip when the remainder looks like a real upstream
        # code — at least one letter and one digit so we never butcher pure-
        # alpha prefixes that genuinely end in DVD (none observed in production
        # data so far, but cheap insurance).
        if not _matches_parseable_code(candidate):
            continue
        marker = f"{suffix.lower()}_media_suffix"
        return marker, candidate
    return None


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


def _strip_leading_service_digit(normalized: str) -> str:
    if len(normalized) < 3 or not normalized[0].isdigit():
        return ""
    candidate = normalized[1:]
    return candidate if _matches_parseable_code(candidate) else ""


def _strip_leading_rental_r(normalized: str) -> str:
    if len(normalized) < 4 or not normalized.startswith("R"):
        return ""
    candidate = normalized[1:]
    match = CODE_RE.match(candidate)
    if not match:
        return ""
    prefix = match.group(1)
    return candidate if prefix in RENTAL_R_STRIPPABLE_PREFIXES else ""


def _strip_leading_9_bluray(normalized: str) -> str:
    if len(normalized) < 4 or not normalized.startswith("9"):
        return ""
    candidate = normalized[1:]
    match = CODE_RE.match(candidate)
    if not match:
        return ""
    prefix = match.group(1)
    return candidate if len(prefix) >= 2 else ""


def _strip_bluray_marker(normalized: str) -> tuple[str, str]:
    if match := BLURAY_BD_INFIX_RE.match(normalized):
        prefix, tail = match.groups()
        if prefix in BLURAY_BD_INFIX_PREFIXES:
            return f"{prefix}{tail}", "bluray_bd_infix"
    if match := BLURAY_B_PREFIX_RE.match(normalized):
        prefix, tail = match.groups()
        return f"{prefix}{tail}", "bluray_b_prefix"
    if match := BLURAY_B_SUFFIX_RE.match(normalized):
        prefix, digits = match.groups()
        if prefix in BLURAY_B_SUFFIX_PREFIXES:
            return f"{prefix}{digits}", "bluray_b_suffix"
    return "", ""


def _matches_parseable_code(normalized: str) -> bool:
    return bool(CODE_RE.match(normalized) or ALNUM_CODE_RE.match(normalized))


def _group_safe_variants(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ungroupable: list[dict[str, Any]] = []
    for item in items:
        if not item.get("_variant_groupable"):
            ungroupable.append(item)
            continue
        groups[str(item.get("canonical_code") or item.get("display_code") or "")].append(item)

    # Salvage pass: items whose code couldn't be canonicalised (e.g. an upstream
    # mis-parse stored the DMM digital padded-id as `3-5` for jums00154) often
    # still share a clean title + runtime with a sibling that DID canonicalise.
    # Attach those orphans to the matching canon-code group so variant merging
    # surfaces them as one movie instead of an orphan card with a garbled code.
    orphans = ungroupable
    ungroupable = []
    for orphan in orphans:
        target = _find_title_runtime_match(orphan, groups)
        if target is not None:
            # `_cluster_same_movie_variants` requires canonical_code equality —
            # adopt the target group's code on the orphan so clustering treats
            # it as a variant. Display-facing fields (display_code, dvd_id) are
            # left untouched so the user still sees the original garbled label
            # in the variant breakdown.
            anchor = target[0]
            orphan["canonical_code"] = anchor.get("canonical_code")
            target.append(orphan)
        else:
            ungroupable.append(orphan)

    result: list[tuple[int, dict[str, Any]]] = [
        (_input_index(item), item) for item in ungroupable
    ]

    for group_items in groups.values():
        for cluster in _cluster_same_movie_variants(group_items):
            if len(cluster) == 1:
                result.append((_input_index(cluster[0]), cluster[0]))
                continue
            ordered = sorted(cluster, key=_sort_key)
            primary = copy.deepcopy(ordered[0])
            visible_items = [_strip_internal_fields(copy.deepcopy(item)) for item in ordered]
            primary["variant_group_count"] = len(visible_items)
            primary["variant_group_items"] = visible_items
            result.append((min(_input_index(item) for item in cluster), primary))
    return [_strip_internal_fields(item) for _, item in sorted(result, key=lambda entry: entry[0])]


def _find_title_runtime_match(
    orphan: dict[str, Any],
    groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]] | None:
    """Return the canon-code group whose title + runtime match `orphan`, else None.

    Strict equality on a non-trivial title-key is the safety belt — short or empty
    titles are rejected outright to prevent accidental merges of unrelated movies
    with similar fragments. Runtime, when present on both sides, must agree within
    the same 5% tolerance the standard cluster check uses.
    """
    title_key = str(orphan.get("_variant_title_key") or "")
    if len(title_key) < 10:
        return None
    orphan_runtime = _runtime_minutes(orphan.get("runtime_mins"))
    best: list[dict[str, Any]] | None = None
    for group in groups.values():
        if not group:
            continue
        matched = [
            item for item in group if str(item.get("_variant_title_key") or "") == title_key
        ]
        if not matched:
            continue
        if orphan_runtime:
            ok = True
            for item in matched:
                item_runtime = _runtime_minutes(item.get("runtime_mins"))
                if not item_runtime:
                    continue
                tolerance = max(3, round(max(orphan_runtime, item_runtime) * 0.05))
                if abs(orphan_runtime - item_runtime) > tolerance:
                    ok = False
                    break
            if not ok:
                continue
        # Prefer the group whose canonical_code looks well-formed (letters+digits)
        # — that's the "real" code the orphan should hang off of.
        if best is None:
            best = group
            continue
        if _group_code_confidence(group) > _group_code_confidence(best):
            best = group
    return best


def _group_code_confidence(group: list[dict[str, Any]]) -> int:
    """Higher score = code looks more like a real product number (letters+digits)."""
    if not group:
        return 0
    sample = group[0]
    canon = str(sample.get("canonical_code") or "")
    if not canon:
        return 0
    has_letters = any(ch.isalpha() for ch in canon)
    has_digits = any(ch.isdigit() for ch in canon)
    if has_letters and has_digits:
        return 2
    if has_letters or has_digits:
        return 1
    return 0


def _cluster_same_movie_variants(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(items) <= 1:
        return [items]

    parents = list(range(len(items)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left in range(len(items)):
        for right in range(left + 1, len(items)):
            if _same_movie(items[left], items[right]):
                union(left, right)

    clusters_by_root: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, item in enumerate(items):
        clusters_by_root[find(index)].append(item)
    return sorted(clusters_by_root.values(), key=lambda cluster: min(_input_index(item) for item in cluster))


def _same_movie(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if str(left.get("canonical_code") or "") != str(right.get("canonical_code") or ""):
        return False
    # Same physical product listed twice (typically mono vs digital storefront):
    # identical dvd_id plus identical release date is decisive on its own. DMM
    # runtime figures routinely disagree between the two listings (the mono
    # page often carries a shorter/rounded figure), so the runtime tolerance
    # must not veto this case.
    if _same_release_identity(left, right):
        return True
    return _safe_group([left, right])


def _same_release_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_dvd = _normalize(left.get("dvd_id"))
    right_dvd = _normalize(right.get("dvd_id"))
    if not left_dvd or left_dvd != right_dvd:
        return False
    left_date = str(left.get("release_date") or "").strip()
    right_date = str(right.get("release_date") or "").strip()
    return bool(left_date) and left_date == right_date


def _safe_group(items: list[dict[str, Any]]) -> bool:
    titles = [str(item.get("_variant_title_key") or "") for item in items]
    non_empty_titles = [title for title in titles if title]
    if len(non_empty_titles) < 2:
        titles_match = True
    else:
        base = max(non_empty_titles, key=len)
        threshold = 0.9 if any(_needs_stronger_title_evidence(item) for item in items) else 0.56
        titles_match = all(_title_similarity(base, title) >= threshold for title in non_empty_titles)
    if not titles_match:
        return False

    # Supplement-origin runtimes are known to carry partial scrapes (half-disc
    # figures, "BEST" excerpt durations, etc.) and shouldn't veto a merge that
    # the trusted r18/mono/digital runtimes agree on. Skip them in the tolerance
    # check; they're advisory, not authoritative.
    runtimes = [
        _runtime_minutes(item.get("runtime_mins"))
        for item in items
        if not _is_supplement_origin(item)
    ]
    runtimes = [value for value in runtimes if value]
    if len(runtimes) >= 2:
        if not _can_ignore_runtime_divergence_for_bluray(items):
            tolerance = max(3, round(max(runtimes) * 0.05))
            if max(runtimes) - min(runtimes) > tolerance:
                return False

    return True


def _is_supplement_origin(item: dict[str, Any]) -> bool:
    return (
        str(item.get("service_code") or "").lower() == "supplement"
        or str(item.get("data_origin") or "").lower() == "supplement"
    )


def _can_ignore_runtime_divergence_for_bluray(items: list[dict[str, Any]]) -> bool:
    if not any(_has_bluray_marker(item) for item in items):
        return False
    titles = [str(item.get("_variant_title_key") or "") for item in items]
    non_empty_titles = [title for title in titles if title]
    if len(non_empty_titles) < 2:
        return False
    base = max(non_empty_titles, key=len)
    return all(_title_similarity(base, title) >= 0.95 for title in non_empty_titles)


def _has_bluray_marker(item: dict[str, Any]) -> bool:
    markers = item.get("_variant_markers")
    if not isinstance(markers, (list, tuple, set)):
        return False
    return any(marker in BLURAY_MARKERS for marker in markers)


def _is_groupable(analysis: dict[str, Any]) -> bool:
    prefix = str(analysis.get("prefix") or "")
    digits = str(analysis.get("digits") or "")
    if not analysis.get("canonical_code") or not prefix or not digits:
        return False
    return True


def _needs_stronger_title_evidence(item: dict[str, Any]) -> bool:
    raw_code = str(item.get("display_code") or item.get("dvd_id") or item.get("content_id") or "")
    analysis = _analyze_code(raw_code, allow_title_tk=False)
    prefix = str(analysis.get("prefix") or "")
    digits = str(analysis.get("digits") or "")
    numeric = int(digits) if digits.isdigit() else 0
    return bool(prefix in LOW_NUMBER_COLLISION_PREFIXES or (digits and numeric < 100))


def _variant_sort_rank(row: dict[str, Any], labels: list[dict[str, Any]]) -> int:
    keys = {label["key"] for label in labels}
    service = str(row.get("service_code") or "").lower()
    if not keys and service == "mono":
        return 0
    if "digital" in keys:
        return 10
    if "rental" in keys:
        return 20
    if "bod" in keys or "dod" in keys or "blu_ray" in keys:
        return 30
    if "fanza_bonus" in keys or "bonus" in keys:
        return 40
    return 50


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
    # Rental editions append the disc-count marker （2枚組）/（3枚組） to an
    # otherwise identical mono/digital title; it's packaging, not identity.
    title = re.sub(r"[（(]\s*\d+\s*枚組\s*[）)]", "", title)
    # A trailing standalone "BD" token marks the Blu-ray edition of the same
    # work (e.g. "…/白石茉莉奈 BD"); strip it so the keys align.
    title = re.sub(r"[\s　]+BD[\s　]*$", "", title, flags=re.IGNORECASE)
    # DMM mono titles often append "/出演者名" while the digital listing omits
    # it. Items are only ever compared within the same canonical code, so
    # dropping the final slash segment is safe and aligns the two forms.
    title = re.sub(r"[/／][^/／]*$", "", title)
    return re.sub(r"\W+", "", title).lower()


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 1.0
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b))
    return SequenceMatcher(None, a, b).ratio()


def _runtime_minutes(value: Any) -> int | None:
    try:
        minutes = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return minutes if minutes > 0 else None
