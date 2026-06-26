"""Ownership lookup against the 115/Emby inventory ledger (`inventory_videos`).

`movie_resources` (the legacy P4 ledger) is empty in production; the real
"what's in my library" signal lives in `inventory_videos`. Matching is by
normalized content_id only — `inventory_videos.actress_id` is a different id
namespace than the JavInfo catalog actress_id, so it must NOT scope the lookup.
"""
from __future__ import annotations

import re

from database.base import get_db


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def codes_in_inventory(codes: list[str]) -> set[str]:
    """Return the subset of `codes` (verbatim) present in `inventory_videos`,
    compared by normalized content_id. Empty/blank inputs never hit the DB."""
    norm_to_originals: dict[str, list[str]] = {}
    for code in codes:
        key = _norm(code)
        if key:
            norm_to_originals.setdefault(key, []).append(code)
    if not norm_to_originals:
        return set()
    matched: set[str] = set()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT regexp_replace(lower(content_id), '[^a-z0-9]', '', 'g') AS n
            FROM inventory_videos
            WHERE content_id IS NOT NULL
              AND regexp_replace(lower(content_id), '[^a-z0-9]', '', 'g') = ANY(%s)
            """,
            (list(norm_to_originals.keys()),),
        )
        for row in cursor.fetchall():
            for original in norm_to_originals.get(row["n"], []):
                matched.add(original)
    return matched
