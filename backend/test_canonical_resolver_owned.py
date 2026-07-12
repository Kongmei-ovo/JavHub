"""Ownership comes only from finalized virtual-film resources."""
from __future__ import annotations

import services.canonical_resolver as resolver


def _films():
    rows = [
        {"content_id": "ppbd00321", "dvd_id": "PPBD-321", "service_code": "digital",
         "data_origin": "native", "actress_ids": [1]},
        {"content_id": "abcd00123", "dvd_id": "ABCD-123", "service_code": "digital",
         "data_origin": "native", "actress_ids": [1]},
    ]
    return resolver.resolve_rows_to_films(rows)


def test_inventory_snapshot_does_not_imply_owned(monkeypatch):
    monkeypatch.setattr(resolver, "codes_with_ready_resource", lambda codes: set())
    owned = resolver.overlay_owned(_films())
    by = {k.upper(): v for k, v in owned.items()}
    assert by["PPBD-321"] is False
    assert by["ABCD-123"] is False


def test_owned_union_with_legacy_ledger(monkeypatch):
    monkeypatch.setattr(resolver, "codes_with_ready_resource",
                        lambda codes: {c for c in codes if "abcd" in c.lower()})
    owned = resolver.overlay_owned(_films())
    assert owned[next(k for k in owned if "ABCD" in k.upper())] is True
