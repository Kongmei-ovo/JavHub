"""Canonical 番号 resolver for the film dictionary (P4-1).

Collapses product-level catalog rows (JavInfoApi is a *product* catalog: one
番号 can appear as several content_ids — Blu-ray / DVD / digital / bonus
editions) into canonical 番号-level *virtual films*, each carrying its member
products. This is a thin orchestration over the mature, existing number-cleaning
and grouping logic — it adds NO new number rules:

  - ``enrich_video_variants`` computes each row's clean ``canonical_code``.
  - ``apply_indexed_variant_groups`` attaches globally-materialized variant
    members (other content_ids of the same 番号 across the whole collection).
  - ``_bucket_key`` folds store-digit editions (``7UMSO-533`` -> ``UMSO-533``)
    onto the base bucket, matching how the variant index buckets, so editions
    collapse even when the index has not been rebuilt.

Read-only: ownership is derived by expanding members against ``movie_resources``
(a canonical is owned when ANY of its member products has a ready resource).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from database.movie_resource import codes_with_ready_resource
from services.video_variant_index import _bucket_key, apply_indexed_variant_groups
from services.video_variants import enrich_video_variants, is_non_movie_item


@dataclass(frozen=True)
class ResolvedFilmMember:
    content_id: str
    dvd_id: str | None
    service_code: str | None


@dataclass
class ResolvedFilm:
    canonical_number: str
    display_code: str
    members: list[ResolvedFilmMember] = field(default_factory=list)
    title: str | None = None
    release_date: str | None = None
    actress_ids: list[int] = field(default_factory=list)
    origin: str = "native"  # native | supplement


def _row_title(row: dict[str, Any]) -> str | None:
    for key in ("title_ja", "title_en", "title"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return None


def _member_content_id(row: dict[str, Any]) -> str:
    """A product's stable key. Pure-supplement (私拍/无码) rows have no DMM
    content_id, so fall back to the dvd_id / canonical 番号 — the same key a
    download would use for such a work."""
    for key in ("content_id", "dvd_id", "canonical_code", "canonical_number"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def resolve_canonical_code(code: str) -> str:
    """Collapse a single content_id or 番号 to its clean canonical 番号.

    Used as the acquisition/ownership key so a 番号's several products (Blu-ray /
    DVD / digital editions) all download into one folder and register one owned
    work. Falls back to the trimmed input when it has no parseable code (e.g. a
    raw private/无码 id), which is still a stable per-work key. No index/DB needed.
    """
    raw = str(code or "").strip()
    if not raw:
        return raw
    enriched = enrich_video_variants(
        [{"content_id": raw, "dvd_id": raw}], variant_mode="flat", include_explanations=False
    )
    if not enriched:
        return raw
    canonical = str(enriched[0].get("canonical_code") or "").strip()
    return _bucket_key(canonical) if canonical else raw


def resolve_rows_to_films(rows: list[dict[str, Any]]) -> list[ResolvedFilm]:
    """Collapse raw catalog rows (native and/or supplement) into canonical
    番号-level virtual films. Deterministic: stable ordering, no randomness."""
    movie_rows = [row for row in (rows or []) if not is_non_movie_item(row)]
    if not movie_rows:
        return []

    # 1) per-row clean canonical_code; 2) attach global variant members.
    enriched = enrich_video_variants(movie_rows, variant_mode="flat", include_explanations=False)
    enriched = apply_indexed_variant_groups(enriched)

    films: dict[str, ResolvedFilm] = {}
    seen_members: dict[str, set[str]] = {}

    for original, item in zip(movie_rows, enriched):
        canonical_code = str(item.get("canonical_code") or "").strip()
        if not canonical_code:
            continue
        bucket = _bucket_key(canonical_code)
        film = films.get(bucket)
        if film is None:
            display = str(item.get("display_code") or item.get("dvd_id") or canonical_code).strip()
            film = ResolvedFilm(
                canonical_number=canonical_code,
                display_code=display or canonical_code,
                origin="native",
            )
            films[bucket] = film
            seen_members[bucket] = set()
        # Prefer the base (non-digit-prefixed) canonical as the reported number.
        if _bucket_key(film.canonical_number) != film.canonical_number and canonical_code == bucket:
            film.canonical_number = canonical_code

        # Members: the indexed group items (whole-collection) plus this row.
        group_items = item.get("variant_group_items")
        member_sources: list[dict[str, Any]] = []
        if isinstance(group_items, list) and group_items:
            member_sources.extend(group_items)
        member_sources.append(original)
        for source in member_sources:
            cid = _member_content_id(source)
            if not cid or cid in seen_members[bucket]:
                continue
            seen_members[bucket].add(cid)
            film.members.append(
                ResolvedFilmMember(
                    content_id=cid,
                    dvd_id=(str(source.get("dvd_id")).strip() or None) if source.get("dvd_id") else None,
                    service_code=(str(source.get("service_code")).strip() or None) if source.get("service_code") else None,
                )
            )

        # Title / earliest release date (deterministic best-of).
        title = _row_title(original)
        if title and not film.title:
            film.title = title
        release = str(original.get("release_date") or "").strip() or None
        if release and (film.release_date is None or release < film.release_date):
            film.release_date = release

        # Actress union + supplement origin.
        for aid in original.get("actress_ids") or []:
            if aid not in film.actress_ids:
                film.actress_ids.append(aid)
        if str(original.get("data_origin") or "").strip() == "supplement":
            film.origin = "supplement"

    # Newest release first, NULL dates last; canonical_number as stable tiebreak.
    ordered = sorted(films.values(), key=lambda f: f.canonical_number)
    ordered.sort(key=lambda f: f.release_date or "", reverse=True)
    return ordered


def resolved_films_to_canonical_set(films: list[ResolvedFilm]) -> set[str]:
    return {film.canonical_number for film in films}


def overlay_owned(films: list[ResolvedFilm]) -> dict[str, bool]:
    """canonical_number -> owned.

    Owned when the canonical key OR any member product has a ready resource.
    The canonical key covers new downloads (P4-2 keys acquisition by canonical);
    the member content_ids cover any legacy product-keyed downloads.
    """
    lookup: list[str] = []
    for film in films:
        lookup.append(film.canonical_number)
        lookup.extend(member.content_id for member in film.members)
    try:
        ready = codes_with_ready_resource(lookup)
    except Exception:
        ready = set()
    return {
        film.canonical_number: (
            film.canonical_number in ready
            or any(member.content_id in ready for member in film.members)
        )
        for film in films
    }
