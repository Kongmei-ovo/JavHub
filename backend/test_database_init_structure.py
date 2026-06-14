from __future__ import annotations

from database import base
from test_support.postgres import make_recording_connection, record_call


def test_init_db_executes_domain_helpers_in_order(monkeypatch):
    calls: list[tuple[str, tuple]] = []
    cursor = object()
    conn = make_recording_connection(calls=calls, cursor=cursor)

    def get_db_orig():
        calls.append(("get_db_orig", ()))
        return conn

    monkeypatch.setattr(base, "_init_translation_and_favorites", record_call("_init_translation_and_favorites", calls))
    monkeypatch.setattr(base, "get_db_orig", get_db_orig)
    monkeypatch.setattr(base, "_init_core_state_tables", record_call("_init_core_state_tables", calls))
    monkeypatch.setattr(base, "_init_inventory_tables", record_call("_init_inventory_tables", calls))
    monkeypatch.setattr(base, "_init_actor_mapping_tables", record_call("_init_actor_mapping_tables", calls))
    monkeypatch.setattr(base, "_init_download_candidate_tables", record_call("_init_download_candidate_tables", calls))
    monkeypatch.setattr(base, "_init_video_variant_tables", record_call("_init_video_variant_tables", calls))
    monkeypatch.setattr(base, "_init_emby_snapshot_tables", record_call("_init_emby_snapshot_tables", calls))
    monkeypatch.setattr(base, "_init_playback_tables", record_call("_init_playback_tables", calls))
    monkeypatch.setattr(base, "_init_movie_resource_tables", record_call("_init_movie_resource_tables", calls))
    monkeypatch.setattr(base, "_init_acquisition_tables", record_call("_init_acquisition_tables", calls))
    monkeypatch.setattr(base, "_init_subscription_baseline_tables", record_call("_init_subscription_baseline_tables", calls))
    monkeypatch.setattr(base, "_migrate_subscriptions", record_call("_migrate_subscriptions", calls))
    monkeypatch.setattr(base, "_create_indexes", record_call("_create_indexes", calls))

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
        ("_init_playback_tables", (cursor,)),
        ("_init_movie_resource_tables", (cursor,)),
        ("_init_acquisition_tables", (cursor,)),
        ("_init_subscription_baseline_tables", (cursor,)),
        ("commit", ()),
        ("close", ()),
        ("_migrate_subscriptions", ()),
        ("_create_indexes", ()),
    ]


def test_init_db_closes_connection_when_schema_helper_fails(monkeypatch):
    calls: list[tuple[str, tuple]] = []
    cursor = object()
    conn = make_recording_connection(calls=calls, cursor=cursor)

    def get_db_orig():
        calls.append(("get_db_orig", ()))
        return conn

    def fail_inventory_tables(_cursor):
        calls.append(("_init_inventory_tables", (_cursor,)))
        raise RuntimeError("schema boom")

    monkeypatch.setattr(base, "_init_translation_and_favorites", record_call("_init_translation_and_favorites", calls))
    monkeypatch.setattr(base, "get_db_orig", get_db_orig)
    monkeypatch.setattr(base, "_init_core_state_tables", record_call("_init_core_state_tables", calls))
    monkeypatch.setattr(base, "_init_inventory_tables", fail_inventory_tables)
    monkeypatch.setattr(base, "_migrate_subscriptions", record_call("_migrate_subscriptions", calls))
    monkeypatch.setattr(base, "_create_indexes", record_call("_create_indexes", calls))

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
        "_init_playback_tables",
        "_init_movie_resource_tables",
        "_init_acquisition_tables",
        "_init_subscription_baseline_tables",
    ]:
        assert callable(getattr(base, name))


def test_create_indexes_registers_inventory_missing_count_sort_index(monkeypatch):
    calls: list[tuple[str, tuple]] = []
    conn = make_recording_connection(calls=calls)
    created: list[str] = []

    monkeypatch.setattr(base, "get_db_orig", lambda: conn)
    monkeypatch.setattr(base, "_create_index_if_possible", lambda _cursor, sql_text: created.append(sql_text))

    base._create_indexes()

    joined = "\n".join(created)
    assert "idx_inventory_actors_missing_count_name" in joined
    assert "inventory_actors(missing_count DESC, actress_name)" in joined
