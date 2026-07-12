"""Per-actress canonical 番号 dictionary (P4-1) — the completeness denominator.

Read-only. Pulls an actress's native catalog rows (product-level) and her
supplement-discovered works (incl. 私拍/无码) directly from the JavInfo import
database, collapses them to canonical 番号-level virtual films via the shared
resolver, and overlays ownership from the local ``movie_resources`` ledger.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query

from database.download_candidate import list_download_candidate_states_by_actress
from services import cache as response_cache
from services.canonical_resolver import (
    ResolvedFilm,
    overlay_owned,
    resolve_rows_to_films,
)
from services.video_variant_index import _connect_import_db, _has_resolved_videos_table

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

        # Resolved half. Native rows already linked in derived_video_actress were
        # counted above; also include resolved r18 rows whose actress association
        # was discovered by a 鸡源 but is absent from the original dump.
        with conn.cursor() as cursor:
            cursor.execute("SELECT to_regclass('resolved_videos') AS reg")
            reg = cursor.fetchone()
            if reg and reg.get("reg"):
                cursor.execute(
                    """
                    SELECT rv.primary_content_id, rv.canonical_number, rv.dvd_id,
                           rv.title_en, rv.title_ja, rv.release_date, rv.service_code,
                           rv.data_origin
                    FROM resolved_videos rv
                    JOIN resolved_video_actresses rva ON rva.resolved_id = rv.resolved_id
                    WHERE rva.local_actress_id = %s
                      AND (
                          rv.data_origin = 'supplement'
                          OR NOT EXISTS (
                              SELECT 1 FROM derived_video_actress dva
                              WHERE dva.content_id = rv.primary_content_id AND dva.actress_id = %s
                          )
                      )
                    """,
                    (actress_id, actress_id),
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
                            "data_origin": (
                                "supplement" if row.get("data_origin") == "supplement" else "native"
                            ),
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


# --- P4-3 completeness: classify gaps against magnet/download state ----------

GAP_TIERS = ("owned", "in_progress", "available", "needs_magnet")


def _norm_number(value) -> str:
    text = str(value or "").upper()
    return "".join(ch for ch in text if ch.isalnum())


def _fetch_actress_candidates(actress_id: int, films: list[ResolvedFilm]) -> list[dict]:
    """All candidate states that can affect this actress's catalog.

    Candidate ownership is movie-level, so include matching acquisition/global
    rows even when their legacy single ``actress_id`` points at another cast
    member (or is NULL).
    """
    content_keys: set[str] = set()
    for film in films:
        content_keys.add(film.canonical_number)
        for member in film.members:
            content_keys.add(member.content_id)
            if member.dvd_id:
                content_keys.add(member.dvd_id)
    return list_download_candidate_states_by_actress(actress_id, content_keys)


def _build_candidate_indexes(candidates: list[dict]) -> tuple[dict, dict]:
    """content_id / normalized-番号 -> every matching candidate."""
    by_cid: dict[str, list[dict]] = {}
    by_number: dict[str, list[dict]] = {}
    for cand in candidates or []:
        cid = str(cand.get("content_id") or "").strip()
        if cid:
            by_cid.setdefault(cid, []).append(cand)
        for key in (cand.get("dvd_id"), cand.get("content_id")):
            num = _norm_number(key)
            if num:
                bucket = by_number.setdefault(num, [])
                if cand not in bucket:
                    bucket.append(cand)
    return by_cid, by_number


def _match_film_candidates(film: ResolvedFilm, by_cid: dict, by_number: dict) -> list[dict]:
    matched: list[dict] = []
    seen: set[int] = set()

    def _add(candidates: list[dict] | None) -> None:
        for cand in candidates or []:
            if id(cand) not in seen:
                seen.add(id(cand))
                matched.append(cand)

    for member in film.members:
        _add(by_cid.get(member.content_id))
        _add(by_number.get(_norm_number(member.content_id)))
        if member.dvd_id:
            _add(by_number.get(_norm_number(member.dvd_id)))
    _add(by_number.get(_norm_number(film.canonical_number)))
    return matched


def classify_film_status(owned: bool, candidates: list[dict]) -> str:
    """owned > in_progress (sent/approved) > available (has magnet) > needs_magnet."""
    if owned:
        return "owned"
    statuses = {str(c.get("status") or "").strip().lower() for c in candidates}
    if statuses & {"sent", "approved"}:
        return "in_progress"
    for cand in candidates:
        if str(cand.get("magnet") or "").strip():
            return "available"
        for alt in cand.get("magnet_alternatives") or []:
            if str(alt.get("magnet") or "").strip():
                return "available"
    return "needs_magnet"


# --- metadata gap (mirrors the frontend movieFieldChips six dimensions) -------

META_FIELDS = (
    ("cover", ("cover_url", "cover_thumb_url")),
    ("runtime", ("runtime_mins",)),
    ("maker", ("maker_name",)),
    ("label", ("label_name",)),
    ("series", ("series_name",)),
    ("category", ("category_names", "genres")),
)

# Series and label are useful display metadata, but they are not defined for
# every release (compilations and one-off products commonly have neither).  A
# missing optional field must not hold the acquisition funnel forever after all
# providers have correctly returned "no value".  Keep reporting these fields in
# ``metadata_missing`` while gating the next stage only on the fields required
# to identify and play a movie reliably.
BLOCKING_META_FIELDS = frozenset({"cover", "runtime", "maker", "category"})


def _has_meta_value(value) -> bool:
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return value is not None and str(value).strip() != ""


def _film_metadata(film: ResolvedFilm, field_rows: dict) -> tuple[str, list[str]]:
    """Return (cover_url, missing_keys) for a canonical film, scanning members.

    Members are unioned best-of: a 番号's several products (digital/rental/Blu-ray)
    may each carry different fields, so the first non-empty value across members
    fills the gap.
    """
    merged: dict = {}
    for member in film.members:
        fields = field_rows.get(member.content_id)
        if fields:
            for k, v in fields.items():
                if _has_meta_value(v) and not _has_meta_value(merged.get(k)):
                    merged[k] = v
    cover = ""
    missing: list[str] = []
    for key, names in META_FIELDS:
        present = any(_has_meta_value(merged.get(n)) for n in names)
        if key == "cover" and present:
            cover = next(str(merged[n]) for n in names if _has_meta_value(merged.get(n)))
        if not present:
            missing.append(key)
    return cover, missing


def _field_row(row: dict, *, with_category: bool) -> dict:
    cats = row.get("category_names") if with_category else None
    if isinstance(cats, str):
        try:
            decoded = json.loads(cats)
            cats = decoded if isinstance(decoded, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            cats = []
    return {
        "cover_url": row.get("cover_url") or "",
        "runtime_mins": row.get("runtime_mins"),
        "maker_name": row.get("maker_name") or "",
        "label_name": row.get("label_name") or "",
        "series_name": row.get("series_name") or "",
        "category_names": list(cats) if cats else [],
    }


def _merge_field_rows(existing: dict | None, incoming: dict | None) -> dict:
    """Best-of merge used when resolved supplement fields augment catalog rows.

    ``resolved_videos`` may contain only the one field a detail provider found;
    replacing the whole native row would therefore lose good catalog metadata.
    """
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if _has_meta_value(value) and not _has_meta_value(merged.get(key)):
            merged[key] = value
    return merged


def _fetch_actress_field_rows(actress_id: int) -> dict:
    """member content_id -> {cover_url, runtime_mins, maker_name, label_name,
    series_name, category_names}, read from the JavInfo import DB.

    Covers native works (derived_video + taxonomy joins, categories aggregated)
    and pure-supplement works (resolved_videos carries denormalized names; it has
    no category column, so category stays a gap there). Best-effort: any read
    failure degrades to the rows gathered so far (=> remaining films report all
    gaps) and never breaks completeness. Tests monkeypatch this."""
    try:
        conn = _connect_import_db()
    except Exception as exc:
        logger.warning("completeness fields: import DB unavailable for actress %s: %s", actress_id, exc)
        return {}
    field_rows: dict[str, dict] = {}
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.content_id,
                       COALESCE(v.jacket_thumb_url, v.jacket_full_url) AS cover_url,
                       v.runtime_mins,
                       COALESCE(mk.name_ja, mk.name_en) AS maker_name,
                       COALESCE(lb.name_ja, lb.name_en) AS label_name,
                       COALESCE(sr.name_ja, sr.name_en) AS series_name,
                       ARRAY_REMOVE(ARRAY_AGG(DISTINCT COALESCE(cat.name_ja, cat.name_en)), NULL)
                           AS category_names
                FROM derived_video v
                JOIN derived_video_actress va ON va.content_id = v.content_id
                LEFT JOIN derived_maker mk ON mk.id = v.maker_id
                LEFT JOIN derived_label lb ON lb.id = v.label_id
                LEFT JOIN derived_series sr ON sr.id = v.series_id
                LEFT JOIN derived_video_category vc ON vc.content_id = v.content_id
                LEFT JOIN derived_category cat ON cat.id = vc.category_id
                WHERE va.actress_id = %s
                GROUP BY v.content_id, cover_url, v.runtime_mins, maker_name, label_name, series_name
                """,
                (actress_id,),
            )
            for row in cursor.fetchall():
                cid = str(row.get("content_id") or "").strip()
                if cid:
                    field_rows[cid] = _field_row(row, with_category=True)

        # Resolved half.  This deliberately includes matched ``r18`` rows: detail
        # jobs write their newly discovered fields to the resolved/supplement
        # layer, so reading only ``data_origin='supplement'`` makes enrichment of
        # native catalog films invisible to completeness forever.
        #
        # A detail-only job can also create a matched resolved row before an
        # actress-link refresh.  The derived_video_actress EXISTS fallback keeps
        # that row visible to the actress that requested the job.
        if _has_resolved_videos_table(conn):
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT ON (rv.resolved_id)
                           rv.primary_content_id, rv.resolved_id, rv.dvd_id, rv.canonical_number,
                           COALESCE(rv.jacket_thumb_url, rv.jacket_full_url) AS cover_url,
                           rv.runtime_mins,
                           COALESCE(rv.maker_name, (
                               SELECT f.field_value FROM supplement_movie_field_values f
                               WHERE f.supplement_movie_id = rv.supplement_movie_id
                                 AND f.field_name = 'maker_name' AND f.field_value <> ''
                               ORDER BY f.confidence DESC, f.fetched_at DESC LIMIT 1
                           )) AS maker_name,
                           COALESCE(rv.label_name, (
                               SELECT f.field_value FROM supplement_movie_field_values f
                               WHERE f.supplement_movie_id = rv.supplement_movie_id
                                 AND f.field_name = 'label_name' AND f.field_value <> ''
                               ORDER BY f.confidence DESC, f.fetched_at DESC LIMIT 1
                           )) AS label_name,
                           COALESCE(rv.series_name, (
                               SELECT f.field_value FROM supplement_movie_field_values f
                               WHERE f.supplement_movie_id = rv.supplement_movie_id
                                 AND f.field_name = 'series_name' AND f.field_value <> ''
                               ORDER BY f.confidence DESC, f.fetched_at DESC LIMIT 1
                           )) AS series_name,
                           (
                               SELECT f.field_value FROM supplement_movie_field_values f
                               WHERE f.supplement_movie_id = rv.supplement_movie_id
                                 AND f.field_name = 'category_names' AND f.field_value <> ''
                               ORDER BY f.confidence DESC, f.fetched_at DESC LIMIT 1
                           ) AS category_names
                    FROM resolved_videos rv
                    LEFT JOIN resolved_video_actresses rva ON rva.resolved_id = rv.resolved_id
                    WHERE rva.local_actress_id = %s
                       OR EXISTS (
                           SELECT 1 FROM derived_video_actress dva
                           WHERE dva.content_id = rv.primary_content_id AND dva.actress_id = %s
                       )
                    ORDER BY rv.resolved_id
                    """,
                    (actress_id, actress_id),
                )
                for row in cursor.fetchall():
                    fields = _field_row(row, with_category=True)
                    for key in (
                        row.get("primary_content_id"),
                        row.get("resolved_id"),
                        row.get("dvd_id"),
                        row.get("canonical_number"),
                    ):
                        k = str(key or "").strip()
                        if k:
                            field_rows[k] = _merge_field_rows(field_rows.get(k), fields)
    except Exception as exc:
        logger.warning("completeness fields: read failed for actress %s: %s", actress_id, exc)
    finally:
        conn.close()
    return field_rows


def _funnel_stage(status: str, metadata_complete: bool) -> str:
    """Field-first funnel: a metadata gap holds a film in 'meta_gap' until fields
    are complete; then it surfaces by acquisition state. Emits the frontend stage
    vocabulary (find_source/downloadable/fetching) so the ③ 下载源 filter chips
    (待找源/可下载/获取中) map 1:1. One film, one stage."""
    if not metadata_complete:
        return "meta_gap"
    if status == "owned":
        return "complete"
    return {
        "needs_magnet": "find_source",
        "available": "downloadable",
        "in_progress": "fetching",
    }.get(status, "find_source")


def _compute_actress_completeness(actress_id: int) -> dict:
    try:
        rows = _fetch_actress_catalog_rows(actress_id)
    except Exception as exc:
        logger.warning("completeness: import DB unavailable for actress %s: %s", actress_id, exc)
        raise HTTPException(status_code=503, detail="catalog database unavailable")

    films = resolve_rows_to_films(rows)
    owned = overlay_owned(films)
    by_cid, by_number = _build_candidate_indexes(_fetch_actress_candidates(actress_id, films))
    field_rows = _fetch_actress_field_rows(actress_id)

    summary = {tier: 0 for tier in GAP_TIERS}
    summary["owned_complete"] = 0
    summary["owned_meta_gap"] = 0
    summary["total"] = len(films)
    summary["owned"] = 0
    summary["stage_fields"] = 0
    summary["stage_sources"] = 0
    summary["stage_complete"] = 0
    payload_films = []
    for film in films:
        is_owned = bool(owned.get(film.canonical_number))
        matched = _match_film_candidates(film, by_cid, by_number)
        status = classify_film_status(is_owned, matched)
        summary[status] += 1
        cover, missing = _film_metadata(film, field_rows)
        blocking_missing = [key for key in missing if key in BLOCKING_META_FIELDS]
        optional_missing = [key for key in missing if key not in BLOCKING_META_FIELDS]
        meta_complete = not blocking_missing             # decoupled from ownership
        if is_owned:
            summary["owned_complete" if meta_complete else "owned_meta_gap"] += 1
        stage = _funnel_stage(status, meta_complete)
        if stage == "meta_gap":
            summary["stage_fields"] += 1
        elif stage == "complete":
            summary["stage_complete"] += 1
        else:
            summary["stage_sources"] += 1
        payload_films.append(
            {
                "canonical_number": film.canonical_number,
                # Show the canonical 番号 (e.g. XVSR-812), not a member's prefixed
                # store form (TKXVSR-812). display_code historically picked the
                # first member's code, which is noisy for merged variant groups.
                "display_code": film.canonical_number,
                "title": film.title,
                "release_date": film.release_date,
                "status": status,
                "candidate_ids": sorted(
                    int(candidate["id"])
                    for candidate in matched
                    if candidate.get("id") is not None
                ),
                "funnel_stage": stage,
                "cover_url": cover,
                "metadata_missing": missing,
                "metadata_blocking_missing": blocking_missing,
                "metadata_optional_missing": optional_missing,
                "metadata_complete": meta_complete,
                "member_count": len(film.members),
                "origin": film.origin,
            }
        )

    return {
        "actress_id": actress_id,
        "total_films": len(films),
        "owned_films": summary["owned"],
        "summary": summary,
        "films": payload_films,
    }


@router.get("/actresses/{actress_id}/completeness")
async def get_actress_completeness(
    actress_id: int,
    cache_control: str | None = Query(None, alias="cache"),
) -> dict:
    """完整度较重(番号归一 + 多表读),而同一演员会被反复请求:补全页每个演员各拉一次、
    作品目录每次操作后 reload。这里按「演员 + 目录/候选/拥有」三个数据代际缓存,任一发生
    变更(下载候选、拥有状态)即自动失效;60s TTL 兜底 115 库存这类无代际的变更。
    get_or_set_response 的 singleflight 还会把并发的相同请求合并成一次计算。"""
    bypass = response_cache.should_bypass_response_cache(cache_control)
    cache_params = {
        "actress_id": actress_id,
        "gen_catalog": await response_cache.get_data_generation_async("javinfo"),
        "gen_candidates": await response_cache.get_data_generation_async("download_candidates"),
        "gen_owned": await response_cache.get_data_generation_async("movie_resources"),
    }

    async def produce():
        return await asyncio.to_thread(_compute_actress_completeness, actress_id)

    return await response_cache.get_or_set_response(
        "film_dictionary_completeness",
        cache_params,
        produce,
        ttl=60,
        bypass=bypass,
    )
