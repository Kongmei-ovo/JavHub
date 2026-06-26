"""Unit test for inventory-backed ownership lookup."""
from __future__ import annotations

import database.inventory_video as iv


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = None

    def execute(self, sql, params=None):
        self.executed = (sql, params)

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._cur = _FakeCursor(rows)

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_codes_in_inventory_matches_by_normalized_content_id(monkeypatch):
    monkeypatch.setattr(iv, "get_db", lambda: _FakeConn([{"n": "ppbd321"}]))
    out = iv.codes_in_inventory(["PPBD-321", "ppbd321", "NOPE-999"])
    assert out == {"PPBD-321", "ppbd321"}


def test_codes_in_inventory_empty_input_skips_db(monkeypatch):
    def _boom():
        raise AssertionError("must not touch DB on empty input")

    monkeypatch.setattr(iv, "get_db", _boom)
    assert iv.codes_in_inventory([]) == set()
    assert iv.codes_in_inventory([None, "", "   "]) == set()
