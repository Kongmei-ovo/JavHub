"""Unit tests for the canonical 番号 resolver (P4-1)."""

from __future__ import annotations

import services.canonical_resolver as resolver
from services.canonical_resolver import (
    ResolvedFilm,
    overlay_owned,
    resolve_rows_to_films,
    resolved_films_to_canonical_set,
)


def _film_by_members(films: list[ResolvedFilm], count: int) -> ResolvedFilm:
    for film in films:
        if len(film.members) == count:
            return film
    raise AssertionError(f"no film with {count} members in {films}")


def test_multiple_products_collapse_to_one_film():
    # Same 番号 (UMSO-533) appears as two products with different content_ids.
    rows = [
        {"content_id": "umso00533", "dvd_id": "UMSO-533", "service_code": "digital", "title_ja": "作品A"},
        {"content_id": "h_999umso00533", "dvd_id": "UMSO-533", "service_code": "rental"},
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1
    film = films[0]
    assert len(film.members) == 2
    assert {m.content_id for m in film.members} == {"umso00533", "h_999umso00533"}
    assert "UMSO" in film.canonical_number.upper()
    assert film.title == "作品A"


def test_single_product_resolves_to_single_member_film():
    rows = [{"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital"}]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1
    assert len(films[0].members) == 1
    assert films[0].members[0].content_id == "abcd00123"


def test_fc2_decoration_yields_clean_canonical():
    rows = [{"content_id": "fc2-ppv-123456", "dvd_id": "FC2-PPV-123456", "service_code": "digital"}]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1
    assert films[0].canonical_number.upper().replace("-", "") == "FC2PPV123456"


def test_unparseable_row_is_dropped():
    rows = [
        {"content_id": "   ", "dvd_id": ""},
        {"content_id": "wxyz00077", "dvd_id": "WXYZ-077", "service_code": "digital"},
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1
    assert "WXYZ" in films[0].canonical_number.upper()


def test_supplement_origin_and_actress_union():
    rows = [
        {
            "content_id": "",
            "dvd_id": "FC2-PPV-998877",
            "canonical_number": "FC2PPV998877",
            "service_code": "supplement",
            "data_origin": "supplement",
            "actress_ids": [42],
        }
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1
    assert films[0].origin == "supplement"
    assert films[0].actress_ids == [42]
    # Pure-supplement member falls back to the dvd_id / 番号 as its key.
    assert films[0].members[0].content_id in {"FC2-PPV-998877", "FC2PPV998877"}


def test_overlay_owned_marks_canonical_when_any_member_ready(monkeypatch):
    rows = [
        {"content_id": "umso00533", "dvd_id": "UMSO-533", "service_code": "digital"},
        {"content_id": "h_999umso00533", "dvd_id": "UMSO-533", "service_code": "rental"},
        {"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital"},
    ]
    films = resolve_rows_to_films(rows)

    # Only the rental edition of UMSO-533 is on disk; ABCD-123 owns nothing.
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {"h_999umso00533"})
    owned = overlay_owned(films)

    canon = resolved_films_to_canonical_set(films)
    umso = next(c for c in canon if "UMSO" in c.upper())
    abcd = next(c for c in canon if "ABCD" in c.upper())
    assert owned[umso] is True
    assert owned[abcd] is False


def test_empty_input_returns_empty():
    assert resolve_rows_to_films([]) == []
    assert overlay_owned([]) == {}


def test_resolve_canonical_code_collapses_editions():
    from services.canonical_resolver import resolve_canonical_code

    # content_id and 番号 forms of the same work share one canonical key.
    assert resolve_canonical_code("umso00533") == resolve_canonical_code("UMSO-533")
    # Unparseable / private id falls back to the trimmed input (still stable).
    assert resolve_canonical_code("  fc2-ppv-998877 ").upper().replace("-", "") == "FC2PPV998877"
    assert resolve_canonical_code("") == ""


def test_overlay_owned_recognizes_canonical_key(monkeypatch):
    # A work downloaded under the new canonical key (not a member content_id).
    rows = [{"content_id": "umso00533", "dvd_id": "UMSO-533", "service_code": "digital"}]
    films = resolve_rows_to_films(rows)
    canonical = films[0].canonical_number

    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: {canonical})
    owned = overlay_owned(films)
    assert owned[canonical] is True


def test_no_dvd_digital_folds_into_dvd_sibling():
    # The digital product has the FANZA maker-bucket prefix and NO dvd_id; its
    # mono sibling carries the authoritative 品番 UMD-934. They must collapse to
    # ONE film whose number is the clean 品番 (not 125UMD-934 / 25UMD-934).
    rows = [
        {"content_id": "125umd00934", "dvd_id": None, "service_code": "digital"},
        {"content_id": "125umd934", "dvd_id": "UMD-934", "service_code": "mono"},
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1, f"expected one merged film, got {[f.canonical_number for f in films]}"
    film = films[0]
    assert film.canonical_number.upper().replace("-", "") == "UMD934"
    assert film.display_code.upper().replace("-", "") == "UMD934"
    assert len(film.members) == 2


def test_backfill_skips_rows_without_a_matching_dvd_sibling():
    # 259LUXU (ラグジュTV) has no de-prefixed LUXU-1234 dvd_id to license a
    # strip, so the data-self-证 backfill must NOT fire: it stays a separate
    # film and is never handed the unrelated UMD work's dvd_id.
    rows = [
        {"content_id": "259luxu1234", "dvd_id": None, "service_code": "digital"},
        {"content_id": "125umd934", "dvd_id": "UMD-934", "service_code": "mono"},
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 2
    luxu = next(f for f in films if "LUXU" in f.canonical_number.upper())
    assert all(m.dvd_id is None for m in luxu.members)  # no UMD dvd fabricated onto it


def test_clean_label_strips_prefix_without_exact_sibling():
    # 125umd1013 has NO UMD-1013 sibling, but UMD is a clean label (UMD-934's
    # dvd_id carries no numeric prefix), so 125 is provably a store prefix and
    # the work resolves to UMD-1013 — not 125UMD-1013.
    rows = [
        {"content_id": "125umd1013", "dvd_id": None, "service_code": "digital"},
        {"content_id": "125umd934", "dvd_id": "UMD-934", "service_code": "mono"},
    ]
    films = resolve_rows_to_films(rows)
    canon = {f.canonical_number.upper().replace("-", "") for f in films}
    assert "UMD1013" in canon
    assert "125UMD1013" not in canon and "25UMD1013" not in canon


def test_digit_prefixed_straggler_folds_into_clean_sibling_film():
    # 57MCSR-627 has no dvd_id anywhere to data-证 a strip, but a clean MCSR-627
    # film exists from another product — the straggler folds onto it (not a guess:
    # the base film is real). No name list involved.
    rows = [
        {"content_id": "mcsr00627", "dvd_id": "MCSR-627", "service_code": "digital"},
        {"content_id": "57mcsr627", "dvd_id": None, "service_code": "mono"},
    ]
    films = resolve_rows_to_films(rows)
    assert len(films) == 1, f"expected one merged film, got {[f.canonical_number for f in films]}"
    assert films[0].canonical_number.upper().replace("-", "") == "MCSR627"
    assert len(films[0].members) == 2


def test_display_code_tracks_canonical_number():
    # Display must present the canonical (virtual) 番号, never a member's
    # store-derived form. Holds across a mixed set.
    rows = [
        {"content_id": "umso00533", "dvd_id": "UMSO-533", "service_code": "digital"},
        {"content_id": "h_999umso00533", "dvd_id": "UMSO-533", "service_code": "rental"},
        {"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital"},
    ]
    films = resolve_rows_to_films(rows)
    for film in films:
        assert film.display_code == film.canonical_number
