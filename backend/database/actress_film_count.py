"""Read/write the materialized per-actress 拟合后 canonical 影片数.

Populated by the variant-index rebuild (services.actress_film_count); actress
lists read it instead of recomputing the resolver per request.
"""
from __future__ import annotations

from database.base import get_db


def replace_actress_film_counts(counts: dict[int, int]) -> int:
    """Atomically replace the whole table with ``{actress_id: total_films}``."""
    rows = [(int(aid), int(n)) for aid, n in (counts or {}).items() if aid is not None]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actress_film_counts")
        if rows:
            cursor.executemany(
                """
                INSERT INTO actress_film_counts (actress_id, total_films, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                rows,
            )
    return len(rows)


def get_actress_film_counts(actress_ids: list[int]) -> dict[int, int]:
    """Return ``{actress_id: total_films}`` for the materialized subset."""
    ids = [int(a) for a in dict.fromkeys(actress_ids or []) if a is not None]
    if not ids:
        return {}
    out: dict[int, int] = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for offset in range(0, len(ids), 500):
            batch = ids[offset : offset + 500]
            placeholders = ", ".join("?" for _ in batch)
            cursor.execute(
                f"SELECT actress_id, total_films FROM actress_film_counts WHERE actress_id IN ({placeholders})",
                tuple(batch),
            )
            for row in cursor.fetchall():
                out[int(row["actress_id"])] = int(row["total_films"])
    return out


