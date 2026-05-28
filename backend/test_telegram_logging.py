from __future__ import annotations

import ast
from pathlib import Path
import unittest


SEARCH_HANDLER = Path(__file__).parent / "telegram_bot" / "handlers" / "search.py"


class TelegramSearchLoggingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = ast.parse(SEARCH_HANDLER.read_text())

    def test_search_handler_uses_module_logger(self) -> None:
        for node in self.tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "logger" for target in node.targets):
                continue
            value = node.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "getLogger"
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == "logging"
                and len(value.args) == 1
                and isinstance(value.args[0], ast.Name)
                and value.args[0].id == "__name__"
            ):
                return

        self.fail("telegram_bot.handlers.search should define logger = logging.getLogger(__name__)")

    def test_search_handler_does_not_write_to_process_streams(self) -> None:
        writes: list[str] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                writes.append(f"print on line {node.lineno}")
            if (
                isinstance(node, ast.Attribute)
                and node.attr in {"stdout", "stderr"}
                and isinstance(node.value, ast.Name)
                and node.value.id == "sys"
            ):
                writes.append(f"sys.{node.attr} on line {node.lineno}")

        self.assertEqual([], writes)
