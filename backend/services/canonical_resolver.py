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

import re
from dataclasses import dataclass, field
from typing import Any

from database.inventory_video import codes_in_inventory
from database.movie_resource import codes_with_ready_resource
from services.video_variant_index import _bucket_key, apply_indexed_variant_groups
from services.video_variants import (
    backfill_dvd_id_from_siblings,
    enrich_video_variants,
    is_non_movie_item,
)


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

    # 0) Lend a no-dvd_id digital product its sibling's authoritative 品番 so the
    #    FANZA maker-bucket prefix (125umd…) collapses onto the clean code and the
    #    two products merge instead of splitting (125UMD-934 vs UMD-934).
    movie_rows = backfill_dvd_id_from_siblings(movie_rows)

    # 1) per-row clean canonical_code; 2) attach global variant members.
    enriched = enrich_video_variants(movie_rows, variant_mode="flat", include_explanations=False)
    enriched = apply_indexed_variant_groups(enriched)

    films: dict[str, ResolvedFilm] = {}
    seen_members: dict[str, set[str]] = {}

    for original, item in zip(movie_rows, enriched):
        row_origin = (
            "supplement"
            if str(original.get("data_origin") or "").strip() == "supplement"
            else "native"
        )
        # ``enrich_video_variants`` uses title evidence to collapse store-only
        # TK/BTK and physical-media editions. Re-resolving their dvd_id here
        # without the title used to undo that decision. For ordinary digital
        # maker-bucket ids, however, the backfilled dvd_id remains the stronger
        # authority (125umd1013 must become UMD-1013, not 25UMD-1013).
        enriched_code = str(item.get("canonical_code") or "").strip()
        edition_keys = {
            "rental", "bod", "dod", "blu_ray", "dvd", "tower_bonus",
            "hmv_bonus", "amazon_bonus", "tsutaya_bonus", "rakuten_bonus",
            "deluxe_pack", "special_edition", "fanza_bonus", "bonus", "outlet",
        }
        labels = item.get("variant_labels") or []
        trust_enriched = bool(item.get("variant_indexed")) or any(
            str(label.get("key") or "") in edition_keys
            for label in labels
            if isinstance(label, dict)
        )
        dvd = str(original.get("dvd_id") or "").strip()
        canonical_code = enriched_code if trust_enriched else (resolve_canonical_code(dvd) if dvd else enriched_code)
        if not canonical_code:
            continue
        bucket = _bucket_key(canonical_code)
        film = films.get(bucket)
        if film is None:
            # Present the canonical (virtual) 番号 itself — never a member's
            # store-derived form (TKXVSR-815 / 125UMD-934). Selection happens
            # upstream in the resolver; the UI just renders display_code.
            film = ResolvedFilm(
                canonical_number=canonical_code,
                display_code=canonical_code,
                origin=row_origin,
            )
            films[bucket] = film
            seen_members[bucket] = set()
        # Prefer the base (non-digit-prefixed) canonical as the reported number.
        if _bucket_key(film.canonical_number) != film.canonical_number and canonical_code == bucket:
            film.canonical_number = canonical_code
            film.display_code = canonical_code

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

        # Actress union + source origin. Native/DMM membership wins: AVBase can
        # enrich or rediscover a work that already exists in the bundled DMM
        # catalog, but that must not turn the whole canonical film into a
        # supplement-only item. Only films whose every row is supplement remain
        # ``supplement``.
        for aid in original.get("actress_ids") or []:
            if aid not in film.actress_ids:
                film.actress_ids.append(aid)
        if row_origin == "native":
            film.origin = "native"

    # Second pass — fold a digit-prefixed straggler (57MCSR-627) onto an existing
    # clean sibling film (MCSR-627) when that base film really exists. The base is
    # a real sibling, not a guess, so 259LUXU-1234 keeps its digits (no LUXU-1234
    # film to adopt it). Covers no-dvd works that pass 1 couldn't data-证.
    canon_to_bucket = {film.canonical_number: bkey for bkey, film in films.items()}
    for bkey, film in list(films.items()):
        if bkey not in films:
            continue  # already merged away
        base = re.sub(r"^\d+", "", film.canonical_number)
        if base == film.canonical_number or base not in canon_to_bucket:
            continue
        target = films.get(canon_to_bucket[base])
        if target is None or target is film:
            continue
        existing = {member.content_id for member in target.members}
        for member in film.members:
            if member.content_id not in existing:
                existing.add(member.content_id)
                target.members.append(member)
        for aid in film.actress_ids:
            if aid not in target.actress_ids:
                target.actress_ids.append(aid)
        if film.title and not target.title:
            target.title = film.title
        if film.release_date and (target.release_date is None or film.release_date < target.release_date):
            target.release_date = film.release_date
        if film.origin == "native":
            target.origin = "native"
        del films[bkey]

    # Newest release first, NULL dates last; canonical_number as stable tiebreak.
    ordered = sorted(films.values(), key=lambda f: f.canonical_number)
    ordered.sort(key=lambda f: f.release_date or "", reverse=True)
    return ordered


def resolved_films_to_canonical_set(films: list[ResolvedFilm]) -> set[str]:
    return {film.canonical_number for film in films}


def overlay_owned(films: list[ResolvedFilm]) -> dict[str, bool]:
    """canonical_number -> owned.

    Owned when the canonical key OR any member product is present in EITHER the
    115/Emby inventory (`inventory_videos`, the real library signal) or the
    legacy `movie_resources` ledger. The canonical key covers canonical-keyed
    downloads (P4-2); member content_ids cover any product-keyed legacy rows.
    """
    lookup: list[str] = []
    for film in films:
        lookup.append(film.canonical_number)
        lookup.extend(member.content_id for member in film.members)
    try:
        ready = set(codes_with_ready_resource(lookup))
    except Exception:
        ready = set()
    try:
        ready |= set(codes_in_inventory(lookup))
    except Exception:
        pass
    return {
        film.canonical_number: (
            film.canonical_number in ready
            or any(member.content_id in ready for member in film.members)
        )
        for film in films
    }
