#!/usr/bin/env python3
"""Analyze JavInfo video code variants from the derived_video table."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import getpass
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


LETTER_NUMBER_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
FC2_RE = re.compile(r"(?i)\bFC2(?:[-_\s]*PPV)?[-_\s]*([0-9]{3,})\b")
FC2_NORMALIZED_RE = re.compile(r"^FC2(?:PPV)?([0-9]+)$")


@dataclasses.dataclass(frozen=True)
class CodeAnalysis:
    raw: str
    normalized: str
    family: str
    label_prefix: str
    numeric: str
    base_normalized: str
    base_display: str
    variants: tuple[str, ...] = ()


def normalize_alias(raw: str) -> str:
    raw = str(raw or "").strip()
    if ":" in raw:
        raw = raw.rsplit(":", 1)[1].strip()
    return "".join(ch.upper() for ch in raw if ch.isalnum())


def trim_padding(digits: str) -> str:
    trimmed = str(digits or "").lstrip("0")
    return trimmed or "0"


def display_censored(prefix: str, digits: str) -> str:
    if not prefix or not digits:
        return ""
    return f"{prefix}-{digits}"


def display_fc2(digits: str) -> str:
    return f"FC2-PPV-{trim_padding(digits)}"


def analyze_code(raw: str) -> CodeAnalysis:
    original = str(raw or "").strip()
    normalized = normalize_alias(original)
    if not normalized:
        return CodeAnalysis(original, "", "unknown", "", "", "", "", ())

    if match := FC2_RE.search(original):
        digits = trim_padding(match.group(1))
        return CodeAnalysis(original, normalized, "fc2", "FC2PPV", digits, "FC2PPV" + digits, display_fc2(digits), ())
    if match := FC2_NORMALIZED_RE.match(normalized):
        digits = trim_padding(match.group(1))
        return CodeAnalysis(original, normalized, "fc2", "FC2PPV", digits, "FC2PPV" + digits, display_fc2(digits), ())

    working = normalized
    variants: list[str] = []

    if working.startswith("TK") and len(working) > 2 and working[2].isalpha():
        variants.append("fanza_limited_tk_prefix")
        working = working[2:]

    if working.startswith("4") and len(working) > 1 and working[1].isalpha():
        variants.append("rental_4_prefix")
        working = working[1:]

    if working.endswith("BOD") and len(working) > 3:
        variants.append("bod_suffix")
        working = working[:-3]

    match = LETTER_NUMBER_RE.match(working)
    if match:
        prefix, raw_digits = match.groups()
        digits = trim_padding(raw_digits)
        if len(raw_digits) > max(3, len(digits)) and raw_digits.startswith("0"):
            variants.append("dmm_padded_digits")
        base = prefix + digits
        return CodeAnalysis(
            original,
            normalized,
            "censored_jp",
            prefix,
            digits,
            base,
            display_censored(prefix, digits),
            tuple(dict.fromkeys(variants)),
        )

    return CodeAnalysis(original, normalized, "unknown", "", "", normalized, original.upper(), tuple(dict.fromkeys(variants)))


def row_code(row: dict[str, Any]) -> str:
    return str(row.get("dvd_id") or row.get("content_id") or "").strip()


def variant_edges(analysis: CodeAnalysis) -> tuple[str, str]:
    if not analysis.normalized or not analysis.base_normalized:
        return "", ""
    if analysis.normalized == analysis.base_normalized:
        return "", ""
    if analysis.normalized.endswith(analysis.base_normalized):
        return analysis.normalized[: -len(analysis.base_normalized)], ""
    if analysis.normalized.startswith(analysis.base_normalized):
        return "", analysis.normalized[len(analysis.base_normalized) :]
    return "", ""


def effective_row_variants(row: dict[str, Any], analysis: CodeAnalysis) -> tuple[str, ...]:
    variants: list[str] = []
    content_id = normalize_alias(str(row.get("content_id") or ""))
    dvd_id = normalize_alias(str(row.get("dvd_id") or ""))
    if "dmm_padded_digits" in analysis.variants:
        if dvd_id:
            variants.append("padded_digits_in_dvd_id")
        elif content_id:
            variants.append("dmm_content_id_padded")
        else:
            variants.append("dmm_padded_digits")
    for variant in analysis.variants:
        if variant != "dmm_padded_digits":
            variants.append(variant)
    return tuple(dict.fromkeys(variants))


def compact_sample(row: dict[str, Any], analysis: CodeAnalysis) -> dict[str, Any]:
    return {
        "content_id": row.get("content_id"),
        "dvd_id": row.get("dvd_id"),
        "code": row_code(row),
        "base": analysis.base_display,
        "variants": list(effective_row_variants(row, analysis)),
        "service_code": row.get("service_code"),
        "release_date": stringify(row.get("release_date")),
        "runtime_mins": row.get("runtime_mins"),
        "title_ja": row.get("title_ja"),
    }


def stringify(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def counter_items(counter: collections.Counter, limit: int) -> list[dict[str, Any]]:
    return [{"value": key, "count": count} for key, count in counter.most_common(limit)]


def connect(settings: dict[str, Any]):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    attempts = [settings]
    current_user = getpass.getuser()
    if settings.get("user") != current_user:
        fallback = dict(settings)
        fallback["user"] = current_user
        fallback["password"] = os.getenv("PGPASSWORD", "")
        attempts.append(fallback)

    errors: list[str] = []
    for attempt in attempts:
        try:
            conn = psycopg2.connect(
                host=attempt["host"],
                port=int(attempt["port"]),
                dbname=attempt["database"],
                user=attempt["user"],
                password=attempt.get("password", ""),
                cursor_factory=RealDictCursor,
            )
            return conn, attempt
        except Exception as exc:  # pragma: no cover - depends on local Postgres roles
            errors.append(f"user={attempt.get('user')}: {exc}")
    raise SystemExit("Could not connect to JavInfo database:\n" + "\n".join(errors))


def default_db_settings() -> dict[str, Any]:
    try:
        from config import config

        cfg = dict(config.javinfo_import_db)
    except Exception:
        cfg = {}
    return {
        "host": os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or cfg.get("host") or "localhost",
        "port": os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or cfg.get("port") or 5432,
        "database": os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or cfg.get("database") or "r18",
        "user": os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or cfg.get("user") or getpass.getuser(),
        "password": os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or cfg.get("password") or "",
    }


def fetch_rows(conn, sample_limit: int | None = None) -> Iterable[dict[str, Any]]:
    where = ""
    limit_clause = ""
    params: tuple[Any, ...] = ()
    if sample_limit:
        limit_clause = " LIMIT %s"
        params = (sample_limit,)
    query = f"""
        SELECT content_id, dvd_id, title_ja, release_date, runtime_mins, service_code, jacket_thumb_url
        FROM derived_video
        {where}
        ORDER BY content_id
        {limit_clause}
    """
    cursor = conn.cursor(name="video_code_variant_scan")
    cursor.itersize = 10000
    cursor.execute(query, params)
    try:
        for row in cursor:
            yield dict(row)
    finally:
        cursor.close()


def analyze_database(conn, *, top: int, sample_limit: int | None = None) -> dict[str, Any]:
    service_counts: collections.Counter[str] = collections.Counter()
    family_counts: collections.Counter[str] = collections.Counter()
    label_prefix_counts: collections.Counter[str] = collections.Counter()
    variant_counts: collections.Counter[str] = collections.Counter()
    wrapper_prefix_counts: collections.Counter[str] = collections.Counter()
    wrapper_suffix_counts: collections.Counter[str] = collections.Counter()
    signature_counts: collections.Counter[str] = collections.Counter()
    family_services: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    family_variants: dict[str, set[str]] = collections.defaultdict(set)
    family_codes: dict[str, set[str]] = collections.defaultdict(set)
    family_samples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    variant_samples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    prefix_samples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    suffix_samples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    rows = 0
    unique_content_ids: set[str] = set()
    unique_dvd_ids: set[str] = set()

    for row in fetch_rows(conn, sample_limit):
        rows += 1
        content_id = str(row.get("content_id") or "").strip()
        dvd_id = str(row.get("dvd_id") or "").strip()
        if content_id:
            unique_content_ids.add(content_id)
        if dvd_id:
            unique_dvd_ids.add(dvd_id)

        analysis = analyze_code(row_code(row))
        family = analysis.base_normalized or analysis.normalized or row_code(row)
        service = str(row.get("service_code") or "")
        service_counts[service] += 1
        family_counts[family] += 1
        if analysis.label_prefix:
            label_prefix_counts[analysis.label_prefix] += 1
        family_services[family][service] += 1
        family_codes[family].add(row_code(row))

        row_variants = effective_row_variants(row, analysis)
        if row_variants:
            family_variants[family].update(row_variants)
            for variant in row_variants:
                variant_counts[variant] += 1
                if len(variant_samples[variant]) < 8:
                    variant_samples[variant].append(compact_sample(row, analysis))
        else:
            family_variants[family].add("standard")

        prefix, suffix = variant_edges(analysis)
        if prefix:
            wrapper_prefix_counts[prefix] += 1
            if len(prefix_samples[prefix]) < 8:
                prefix_samples[prefix].append(compact_sample(row, analysis))
        if suffix:
            wrapper_suffix_counts[suffix] += 1
            if len(suffix_samples[suffix]) < 8:
                suffix_samples[suffix].append(compact_sample(row, analysis))

        if len(family_samples[family]) < 10:
            family_samples[family].append(compact_sample(row, analysis))

    for family, count in family_counts.items():
        if count > 1:
            variants = sorted(family_variants.get(family) or {"standard"})
            services = sorted(service for service, n in family_services[family].items() if n)
            signature_counts["+".join(variants) + " | " + "+".join(services)] += 1

    top_families = []
    for family, count in family_counts.most_common(top * 5):
        if count <= 1:
            continue
        samples = family_samples[family]
        top_families.append(
            {
                "base": samples[0]["base"] if samples else family,
                "base_key": family,
                "count": count,
                "distinct_codes": sorted(family_codes[family])[:20],
                "services": dict(family_services[family].most_common()),
                "variants": sorted(family_variants.get(family) or []),
                "samples": samples,
            }
        )
        if len(top_families) >= top:
            break

    variant_family_count = sum(1 for count in family_counts.values() if count > 1)
    rows_in_variant_families = sum(count for count in family_counts.values() if count > 1)
    result = {
        "summary": {
            "rows_scanned": rows,
            "unique_content_ids": len(unique_content_ids),
            "unique_dvd_ids": len(unique_dvd_ids),
            "base_families": len(family_counts),
            "families_with_more_than_one_row": variant_family_count,
            "rows_in_multi_row_families": rows_in_variant_families,
            "max_family_size": max(family_counts.values(), default=0),
            "distinct_label_prefixes": len(label_prefix_counts),
            "distinct_wrapper_prefixes": len(wrapper_prefix_counts),
            "distinct_wrapper_suffixes": len(wrapper_suffix_counts),
        },
        "service_counts": counter_items(service_counts, top),
        "variant_counts": counter_items(variant_counts, top),
        "wrapper_prefix_counts": counter_items(wrapper_prefix_counts, top),
        "wrapper_suffix_counts": counter_items(wrapper_suffix_counts, top),
        "label_prefix_counts": counter_items(label_prefix_counts, top),
        "multi_row_family_signatures": counter_items(signature_counts, top),
        "top_multi_row_families": top_families,
        "variant_samples": {key: value for key, value in variant_samples.items()},
        "wrapper_prefix_samples": {key: value for key, value in prefix_samples.items()},
        "wrapper_suffix_samples": {key: value for key, value in suffix_samples.items()},
    }
    return result


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_None._\n"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(col, "")).replace("|", "\\|") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Video Code Variant Analysis",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Service Codes",
            "",
            markdown_table(report["service_counts"], ["value", "count"]),
            "## Variant Types",
            "",
            markdown_table(report["variant_counts"], ["value", "count"]),
            "## Wrapper Prefixes",
            "",
            markdown_table(report["wrapper_prefix_counts"], ["value", "count"]),
            "## Wrapper Suffixes",
            "",
            markdown_table(report["wrapper_suffix_counts"], ["value", "count"]),
            "## Label Prefixes",
            "",
            markdown_table(report["label_prefix_counts"], ["value", "count"]),
            "## Multi-row Family Signatures",
            "",
            markdown_table(report["multi_row_family_signatures"], ["value", "count"]),
            "## Top Multi-row Families",
            "",
        ]
    )
    for family in report["top_multi_row_families"]:
        lines.extend(
            [
                f"### {family['base']} ({family['count']})",
                "",
                f"- base_key: {family['base_key']}",
                f"- variants: {', '.join(family['variants'])}",
                f"- services: {json.dumps(family['services'], ensure_ascii=False)}",
                f"- distinct_codes: {', '.join(family['distinct_codes'])}",
                "",
                markdown_table(
                    family["samples"],
                    ["content_id", "dvd_id", "code", "base", "variants", "service_code", "release_date", "runtime_mins", "title_ja"],
                ),
            ]
        )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    defaults = default_db_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-host", default=defaults["host"])
    parser.add_argument("--db-port", type=int, default=int(defaults["port"]))
    parser.add_argument("--db-name", default=defaults["database"])
    parser.add_argument("--db-user", default=defaults["user"])
    parser.add_argument("--db-password", default=defaults["password"])
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--sample-limit", type=int, default=0, help="Scan only the first N rows for quick testing.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    settings = {
        "host": args.db_host,
        "port": args.db_port,
        "database": args.db_name,
        "user": args.db_user,
        "password": args.db_password,
    }
    conn, effective = connect(settings)
    try:
        report = analyze_database(conn, top=max(1, args.top), sample_limit=args.sample_limit or None)
    finally:
        conn.close()

    report["connection"] = {
        "host": effective["host"],
        "port": effective["port"],
        "database": effective["database"],
        "user": effective["user"],
    }
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, default=stringify))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
