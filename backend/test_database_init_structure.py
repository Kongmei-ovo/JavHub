from __future__ import annotations

import ast
from pathlib import Path


def test_init_db_is_decomposed_into_ordered_domain_helpers():
    source = (Path(__file__).parent / "database" / "base.py").read_text()
    module = ast.parse(source)
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    }
    expected_order = [
        "_init_external_databases",
        "_create_download_tables",
        "_create_subscription_and_log_tables",
        "_create_inventory_tables",
        "_create_actor_mapping_tables",
        "_create_download_candidate_tables",
        "_create_video_variant_tables",
        "_create_emby_snapshot_tables",
        "_migrate_subscriptions",
        "_create_indexes",
    ]

    for name in expected_order:
        assert name in functions

    init_source = functions["init_db"]
    positions = [init_source.index(f"{name}(") for name in expected_order]
    assert positions == sorted(positions)
