"""Materialize per-actress 拟合后 canonical 影片数 in a single pass.

The count is ``distinct _bucket_key(enrich_video_variants(row).canonical_code)``
over an actress's catalog rows — exactly what ``resolve_rows_to_films`` collapses
to, but computed once for the whole collection instead of per request. The
variant-edition merge (TK/特典/BD/store editions) lives entirely in
``enrich_video_variants`` when it sees the full row (title etc.), so a single
flat enrich of every video yields each video's canonical; we then count distinct
canonicals per actress.

Run during the variant-index rebuild (and on demand) to fill
``actress_film_counts``.
"""
from __future__ import annotations

import logging

from database.actress_film_count import get_actress_film_counts, replace_actress_film_counts
from services.video_variant_index import _connect_import_db, _bucket_key
from services.video_variants import enrich_video_variants, is_non_movie_item

logger = logging.getLogger(__name__)


def overlay_movie_counts(items, id_keys=("id", "actress_id", "entity_id")) -> list:
    """Replace each actress item's raw 商品 movie_count with the materialized
    拟合后 canonical count when available. Best-effort + in-place: a missing
    table or unmaterialized actress just keeps the product count.
    """
    if not items:
        return items

    def pick_id(item):
        for key in id_keys:
            value = item.get(key) if isinstance(item, dict) else None
            if value is not None and str(value).strip() != "":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    ids = [aid for aid in (pick_id(it) for it in items if isinstance(it, dict)) if aid is not None]
    try:
        counts = get_actress_film_counts(ids)
    except Exception as exc:  # noqa: BLE001 - never break the listing on a count read
        logger.debug("overlay_movie_counts: count read failed: %s", exc)
        return items
    if not counts:
        return items
    for item in items:
        if not isinstance(item, dict):
            continue
        aid = pick_id(item)
        if aid in counts:
            item["movie_count"] = counts[aid]
    return items

_ENRICH_CHUNK = 2000


def _canonical_of(row: dict) -> str:
    enriched = enrich_video_variants([row], variant_mode="flat", include_explanations=False)
    if not enriched:
        return ""
    canonical = str(enriched[0].get("canonical_code") or "").strip()
    return _bucket_key(canonical) if canonical else ""


def _build_content_canonicals(conn) -> dict[str, str]:
    """content_id -> bucket canonical, for every native movie row."""
    content_to_canon: dict[str, str] = {}
    cursor = conn.cursor(name="afc_native_scan")
    cursor.itersize = 10000
    cursor.execute(
        """
        SELECT content_id, dvd_id, title_ja, title_en, service_code
        FROM derived_video
        WHERE service_code IS NULL OR service_code <> 'ebook'
        """
    )
    chunk: list[dict] = []

    def flush(rows: list[dict]) -> None:
        movie_rows = [r for r in rows if not is_non_movie_item(r)]
        if not movie_rows:
            return
        enriched = enrich_video_variants(movie_rows, variant_mode="flat", include_explanations=False)
        for src, item in zip(movie_rows, enriched):
            cid = str(src.get("content_id") or "").strip()
            canonical = str(item.get("canonical_code") or "").strip()
            if cid and canonical:
                content_to_canon[cid] = _bucket_key(canonical)

    try:
        for row in cursor:
            chunk.append(dict(row))
            if len(chunk) >= _ENRICH_CHUNK:
                flush(chunk)
                chunk = []
        flush(chunk)
    finally:
        cursor.close()
    return content_to_canon


def _accumulate_actress_films(conn, content_to_canon: dict[str, str]) -> dict[int, set]:
    """actress_id -> set of canonical codes, from the actress→video mapping."""
    actress_films: dict[int, set] = {}
    cursor = conn.cursor(name="afc_pairs_scan")
    cursor.itersize = 20000
    cursor.execute("SELECT content_id, actress_id FROM derived_video_actress")
    try:
        for row in cursor:
            data = dict(row)
            canon = content_to_canon.get(str(data.get("content_id") or "").strip())
            aid = data.get("actress_id")
            if canon and aid is not None:
                actress_films.setdefault(int(aid), set()).add(canon)
    finally:
        cursor.close()
    return actress_films


def rebuild_actress_film_counts() -> dict:
    """Recompute every actress's canonical film count and replace the table.

    Returns summary stats. Raises on a dead import DB (caller decides whether a
    failed count rebuild should fail the whole index job)."""
    conn = _connect_import_db()
    try:
        content_to_canon = _build_content_canonicals(conn)
        actress_films = _accumulate_actress_films(conn, content_to_canon)
    finally:
        conn.close()

    counts = {aid: len(films) for aid, films in actress_films.items()}
    stored = replace_actress_film_counts(counts)
    logger.info(
        "actress film counts rebuilt: %s actresses, %s distinct videos",
        stored,
        len(content_to_canon),
    )
    return {"actresses": stored, "videos": len(content_to_canon)}
