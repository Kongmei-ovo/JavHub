from __future__ import annotations

import ast
from pathlib import Path


TELEGRAM_SEARCH_HANDLER = Path(__file__).parent / "telegram_bot" / "handlers" / "search.py"


def _module_tree() -> ast.Module:
    return ast.parse(TELEGRAM_SEARCH_HANDLER.read_text(encoding="utf-8"))


def _is_name_call(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
    )


def test_telegram_search_handler_does_not_write_directly_to_stdout():
    tree = _module_tree()

    print_calls = [
        node.lineno
        for node in ast.walk(tree)
        if _is_name_call(node, "print")
    ]

    assert print_calls == []


def test_telegram_search_handler_defines_module_logger():
    tree = _module_tree()

    logger_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "logger" for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "getLogger"
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "logging"
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == "__name__"
    ]

    assert len(logger_assignments) == 1
