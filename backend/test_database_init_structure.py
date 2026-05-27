from __future__ import annotations

import inspect

from database import base


def test_init_db_delegates_to_domain_helpers_in_order():
    source = inspect.getsource(base.init_db)
    expected_order = [
        "_init_translation_and_favorites",
        "_init_core_state_tables",
        "_init_inventory_tables",
        "_init_actor_mapping_tables",
        "_init_download_candidate_tables",
        "_init_video_variant_tables",
        "_init_emby_snapshot_tables",
        "_migrate_subscriptions",
        "_create_indexes",
    ]

    positions = [source.index(f"{name}(") for name in expected_order]

    assert positions == sorted(positions)


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
