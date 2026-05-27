from __future__ import annotations

from database import base


class RecordingConnection:
    def __init__(self, calls: list[tuple[str, tuple]], cursor: object):
        self.calls = calls
        self.cursor_obj = cursor

    def cursor(self):
        self.calls.append(("cursor", ()))
        return self.cursor_obj

    def commit(self):
        self.calls.append(("commit", ()))

    def close(self):
        self.calls.append(("close", ()))


def _record_call(name: str, calls: list[tuple[str, tuple]]):
    def record(*args):
        calls.append((name, args))

    return record


def test_init_db_executes_domain_helpers_in_order(monkeypatch):
    calls: list[tuple[str, tuple]] = []
    cursor = object()
    conn = RecordingConnection(calls, cursor)

    def get_db_orig():
        calls.append(("get_db_orig", ()))
        return conn

    monkeypatch.setattr(base, "_init_translation_and_favorites", _record_call("_init_translation_and_favorites", calls))
    monkeypatch.setattr(base, "get_db_orig", get_db_orig)
    monkeypatch.setattr(base, "_init_core_state_tables", _record_call("_init_core_state_tables", calls))
    monkeypatch.setattr(base, "_init_inventory_tables", _record_call("_init_inventory_tables", calls))
    monkeypatch.setattr(base, "_init_actor_mapping_tables", _record_call("_init_actor_mapping_tables", calls))
    monkeypatch.setattr(base, "_init_download_candidate_tables", _record_call("_init_download_candidate_tables", calls))
    monkeypatch.setattr(base, "_init_video_variant_tables", _record_call("_init_video_variant_tables", calls))
    monkeypatch.setattr(base, "_init_emby_snapshot_tables", _record_call("_init_emby_snapshot_tables", calls))
    monkeypatch.setattr(base, "_migrate_subscriptions", _record_call("_migrate_subscriptions", calls))
    monkeypatch.setattr(base, "_create_indexes", _record_call("_create_indexes", calls))

    base.init_db()

    assert calls == [
        ("_init_translation_and_favorites", ()),
        ("get_db_orig", ()),
        ("cursor", ()),
        ("_init_core_state_tables", (cursor,)),
        ("_init_inventory_tables", (cursor,)),
        ("_init_actor_mapping_tables", (cursor,)),
        ("_init_download_candidate_tables", (cursor,)),
        ("_init_video_variant_tables", (cursor,)),
        ("_init_emby_snapshot_tables", (cursor,)),
        ("commit", ()),
        ("close", ()),
        ("_migrate_subscriptions", ()),
        ("_create_indexes", ()),
    ]


def test_init_db_closes_connection_when_schema_helper_fails(monkeypatch):
    calls: list[tuple[str, tuple]] = []
    cursor = object()
    conn = RecordingConnection(calls, cursor)

    def get_db_orig():
        calls.append(("get_db_orig", ()))
        return conn

    def fail_inventory_tables(_cursor):
        calls.append(("_init_inventory_tables", (_cursor,)))
        raise RuntimeError("schema boom")

    monkeypatch.setattr(base, "_init_translation_and_favorites", _record_call("_init_translation_and_favorites", calls))
    monkeypatch.setattr(base, "get_db_orig", get_db_orig)
    monkeypatch.setattr(base, "_init_core_state_tables", _record_call("_init_core_state_tables", calls))
    monkeypatch.setattr(base, "_init_inventory_tables", fail_inventory_tables)
    monkeypatch.setattr(base, "_migrate_subscriptions", _record_call("_migrate_subscriptions", calls))
    monkeypatch.setattr(base, "_create_indexes", _record_call("_create_indexes", calls))

    try:
        base.init_db()
    except RuntimeError as exc:
        assert str(exc) == "schema boom"
    else:
        raise AssertionError("init_db should propagate schema helper failures")

    assert calls == [
        ("_init_translation_and_favorites", ()),
        ("get_db_orig", ()),
        ("cursor", ()),
        ("_init_core_state_tables", (cursor,)),
        ("_init_inventory_tables", (cursor,)),
        ("close", ()),
    ]


def test_database_initializer_helpers_exist():
    for name in [
        "_init_translation_and_favorites",
        "_init_core_state_tables",
        "_init_inventory_tables",
        "_init_actor_mapping_tables",
        "_init_download_candidate_tables",
        "_init_video_variant_tables",
        "_init_emby_snapshot_tables",
    ]:
        assert callable(getattr(base, name))
