from __future__ import annotations

from pathlib import Path


def test_inventory_tasks_use_module_logger_instead_of_prints():
    source = (Path(__file__).parent / "scheduler" / "inventory_tasks.py").read_text()

    assert "logging.getLogger(__name__)" in source
    assert "print(" not in source
    assert "logger.exception(" in source
