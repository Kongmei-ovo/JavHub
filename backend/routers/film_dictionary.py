"""Per-actress canonical 番号 dictionary (P4-1) — the completeness denominator.

Read-only. Pulls an actress's native catalog rows (product-level) and her
supplement-discovered works (incl. 私拍/无码) directly from the JavInfo import
database, collapses them to canonical 番号-level virtual films via the shared
resolver, and overlays ownership from the local ``movie_resources`` ledger.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from services.canonical_resolver import (
    overlay_owned,
    resolve_rows_to_films,
)
from services.video_variant_index import _connect_import_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/film-dictionary", tags=["film-dictionary"])


def _fetch_actress_catalog_rows(actress_id: int) -> list[dict]:
    """Native (derived_video) + supplement (resolved_videos) rows for an actress.

    Each row carries ``actress_ids`` so the resolver can union actresses per
    film. Raises on a dead import DB so the caller can surface 503 rather than
    silently report an empty (=0%) dictionary. Returns [] for an actress with
    no works.
    """
    conn = _connect_import_db()
    rows: list[dict] = []
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.content_id, v.dvd_id, v.title_en, v.title_ja,
                       v.release_date, v.service_code
                FROM derived_video v
                JOIN derived_video_actress va ON v.content_id = va.content_id
                WHERE va.actress_id = %s
                """,
                (actress_id,),
            )
            for row in cursor.fetchall():
                rows.append(
                    {
                        "content_id": row.get("content_id"),
                        "dvd_id": row.get("dvd_id"),
                        "title_en": row.get("title_en"),
                        "title_ja": row.get("title_ja"),
                        "release_date": _as_text(row.get("release_date")),
                        "service_code": row.get("service_code"),
                        "data_origin": "native",
                        "actress_ids": [actress_id],
                    }
                )

        # Supplement half — only when the resolved layer exists. data_origin
        # 'r18' rows already match a native content_id (counted above), so take
        # only pure-supplement works to avoid double counting.
        with conn.cursor() as cursor:
            cursor.execute("SELECT to_regclass('resolved_videos') AS reg")
            reg = cursor.fetchone()
            if reg and reg.get("reg"):
                cursor.execute(
                    """
                    SELECT rv.primary_content_id, rv.canonical_number, rv.dvd_id,
                           rv.title_en, rv.title_ja, rv.release_date, rv.service_code
                    FROM resolved_videos rv
                    JOIN resolved_video_actresses rva ON rva.resolved_id = rv.resolved_id
                    WHERE rva.local_actress_id = %s AND rv.data_origin = 'supplement'
                    """,
                    (actress_id,),
                )
                for row in cursor.fetchall():
                    rows.append(
                        {
                            "content_id": row.get("primary_content_id"),
                            "dvd_id": row.get("dvd_id"),
                            "canonical_number": row.get("canonical_number"),
                            "title_en": row.get("title_en"),
                            "title_ja": row.get("title_ja"),
                            "release_date": _as_text(row.get("release_date")),
                            "service_code": row.get("service_code"),
                            "data_origin": "supplement",
                            "actress_ids": [actress_id],
                        }
                    )
    finally:
        conn.close()
    return rows


def _as_text(value) -> str | None:
    if value is None:
        return None
    return str(value)


@router.get("/actresses/{actress_id}")
def get_actress_film_dictionary(actress_id: int) -> dict:
    try:
        rows = _fetch_actress_catalog_rows(actress_id)
    except Exception as exc:  # import DB unreachable
        logger.warning("film dictionary: import DB unavailable for actress %s: %s", actress_id, exc)
        raise HTTPException(status_code=503, detail="catalog database unavailable")

    films = resolve_rows_to_films(rows)
    owned = overlay_owned(films)

    payload_films = []
    owned_count = 0
    for film in films:
        is_owned = bool(owned.get(film.canonical_number))
        if is_owned:
            owned_count += 1
        payload_films.append(
            {
                "canonical_number": film.canonical_number,
                "display_code": film.display_code,
                "title": film.title,
                "release_date": film.release_date,
                "owned": is_owned,
                "member_count": len(film.members),
                "members": [
                    {
                        "content_id": member.content_id,
                        "dvd_id": member.dvd_id,
                        "service_code": member.service_code,
                    }
                    for member in film.members
                ],
                "origin": film.origin,
                "actress_ids": film.actress_ids,
            }
        )

    return {
        "actress_id": actress_id,
        "total_films": len(films),
        "owned_films": owned_count,
        "films": payload_films,
    }
