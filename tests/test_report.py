"""Тесты отчёта о прямых зависимостях."""

import asyncio
import unittest
from typing import List

from src.graph import build_tree
from src.requirement import parse_requirement
from src.report import (CYCLE_MARK, NO_DEPENDENCIES, TRUNCATED_MARK,
                        format_report, format_summary, format_tree)

METADATA = {"info": {"version": "2.34.2"}}

REQUIREMENTS = [
    parse_requirement("urllib3<3,>=1.26"),
    parse_requirement("certifi>=2023.5.7"),
    parse_requirement('PySocks!=1.5.7,>=1.5.6; extra == "socks"'),
]


class ReportTest(unittest.TestCase):
    """Проверяет состав и порядок строк отчёта."""

    def test_header_order_and_total(self) -> None:
        """Зависимости идут по алфавиту, затем итоговая строка."""
        lines = format_report("requests", METADATA, REQUIREMENTS)
        self.assertEqual(lines, [
            "прямые зависимости пакета requests 2.34.2:",
            "  certifi (>=2023.5.7)",
            "  PySocks (!=1.5.7,>=1.5.6) [extra: socks]",
            "  urllib3 (<3,>=1.26)",
            "всего: 3, базовых: 2, из extras: 1",
        ])

    def test_no_dependencies(self) -> None:
        """Пустой список зависимостей даёт отдельное сообщение."""
        lines = format_report("requests", METADATA, [])
        self.assertEqual(lines[-1], NO_DEPENDENCIES)

    def test_unknown_version(self) -> None:
        """Без версии в метаданных отчёт всё равно строится."""
        lines = format_report("requests", {}, [])
        self.assertIn("версия неизвестна", lines[0])


async def tree_children(name: str) -> List[str]:
    """Отдаёт детей простого дерева A → B, A → C → D."""
    return {"A": ["B", "C"], "B": [], "C": ["D"], "D": []}[name]


async def cycle_children(name: str) -> List[str]:
    """Отдаёт детей дерева с циклом A → B → A."""
    return {"A": ["B"], "B": ["A"]}[name]


class TreeTest(unittest.TestCase):
    """Проверяет печать дерева зависимостей."""

    def test_lines_and_indent(self) -> None:
        """Уровень вложенности задаётся отступом."""
        root = asyncio.run(build_tree(tree_children, "A", 5))
        self.assertEqual(format_tree(root), [
            "A",
            "  B",
            "  C",
            "    D",
        ])

    def test_cycle_mark(self) -> None:
        """Цикл помечается в строке узла."""
        root = asyncio.run(build_tree(cycle_children, "A", 10))
        lines = [line.strip() for line in format_tree(root)]
        self.assertIn("A" + CYCLE_MARK, lines)

    def test_truncated_mark(self) -> None:
        """Обрезка по глубине помечается в строке узла."""
        root = asyncio.run(build_tree(tree_children, "A", 1))
        lines = [line.strip() for line in format_tree(root)]
        self.assertIn("B" + TRUNCATED_MARK, lines)

    def test_summary(self) -> None:
        """Сводка считает узлы и циклы."""
        root = asyncio.run(build_tree(tree_children, "A", 5))
        summary = format_summary(root)[0]
        self.assertIn("узлов: 4", summary)
        self.assertIn("циклов: 0", summary)

    def test_summary_with_cycle(self) -> None:
        """Сводка видит цикл."""
        root = asyncio.run(build_tree(cycle_children, "A", 10))
        self.assertIn("циклов: 1", format_summary(root)[0])
