from __future__ import annotations

import ast
from pathlib import Path


INVENTORY_TASKS = Path(__file__).parent / "scheduler" / "inventory_tasks.py"


def _module_tree() -> ast.Module:
    return ast.parse(INVENTORY_TASKS.read_text(encoding="utf-8"))


def _is_name_call(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
    )


def _is_logger_exception_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "exception"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "logger"
    )


def test_inventory_tasks_do_not_write_directly_to_stdout():
    tree = _module_tree()

    print_calls = [
        node.lineno
        for node in ast.walk(tree)
        if _is_name_call(node, "print")
    ]

    assert print_calls == []


def test_inventory_tasks_define_module_logger():
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


def test_inventory_tasks_log_broad_exceptions_with_tracebacks():
    tree = _module_tree()

    broad_handlers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        and isinstance(node.type, ast.Name)
        and node.type.id == "Exception"
    ]

    assert broad_handlers
    handlers_without_traceback_logging = [
        node.lineno
        for node in broad_handlers
        if not any(_is_logger_exception_call(child) for child in ast.walk(node))
    ]

    assert handlers_without_traceback_logging == []
