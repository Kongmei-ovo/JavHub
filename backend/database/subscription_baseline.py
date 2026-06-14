"""Persistent subscription baseline.

Replaces the old 500-code sliding window: when a subscription is first checked
we record its *entire* current filmography as the baseline (and stamp
``baseline_at``). Anything already in the baseline is "known" and never
re-downloaded; only codes outside it are candidates for追新. The set is
unbounded — old codes are never evicted, so a prolific actress past 500 titles
no longer leaks "new" false positives.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from database.base import get_db


def _normalize_codes(codes: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in codes or []:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def establish_baseline(subscription_id: int, codes: Iterable[str]) -> bool:
    """Record the full filmography as the baseline, once. Idempotent: if a
    baseline already exists it is left untouched and ``False`` is returned."""
    sub_id = int(subscription_id)
    normalized = _normalize_codes(codes)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM subscription_baseline_meta WHERE subscription_id = ? LIMIT 1",
            (sub_id,),
        )
        if cursor.fetchone() is not None:
            return False
        cursor.execute(
            "INSERT INTO subscription_baseline_meta (subscription_id, baseline_at) "
            "VALUES (?, CURRENT_TIMESTAMP)",
            (sub_id,),
        )
        if normalized:
            cursor.executemany(
                "INSERT INTO subscription_baselines (subscription_id, code) "
                "VALUES (?, ?) ON CONFLICT DO NOTHING",
                [(sub_id, code) for code in normalized],
            )
    return True


def is_in_baseline(subscription_id: int, code: str) -> bool:
    value = str(code or "").strip()
    if not value:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM subscription_baselines WHERE subscription_id = ? AND code = ? LIMIT 1",
            (int(subscription_id), value),
        )
        return cursor.fetchone() is not None


def filter_new_against_baseline(subscription_id: int, codes: Iterable[str]) -> list[str]:
    """Return only the codes that are NOT in the baseline, preserving input
    order. Batched IN queries — never scans the whole baseline."""
    sub_id = int(subscription_id)
    ordered = _normalize_codes(codes)
    if not ordered:
        return []
    existing: set[str] = set()
    with get_db() as conn:
        cursor = conn.cursor()
        for offset in range(0, len(ordered), 500):
            batch = ordered[offset : offset + 500]
            placeholders = ", ".join("?" for _ in batch)
            cursor.execute(
                f"SELECT code FROM subscription_baselines "
                f"WHERE subscription_id = ? AND code IN ({placeholders})",
                (sub_id, *batch),
            )
            existing.update(str(row["code"]) for row in cursor.fetchall())
    return [code for code in ordered if code not in existing]


def add_to_baseline(subscription_id: int, code: str) -> None:
    value = str(code or "").strip()
    if not value:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subscription_baselines (subscription_id, code) "
            "VALUES (?, ?) ON CONFLICT DO NOTHING",
            (int(subscription_id), value),
        )


def get_baseline_at(subscription_id: int) -> datetime | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT baseline_at FROM subscription_baseline_meta WHERE subscription_id = ?",
            (int(subscription_id),),
        )
        row = cursor.fetchone()
        return row["baseline_at"] if row else None
