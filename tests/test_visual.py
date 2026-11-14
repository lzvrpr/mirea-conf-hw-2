"""Тесты визуализации: ASCII-дерево, Mermaid и SVG."""

import asyncio
import unittest
from xml.etree.ElementTree import fromstring
from typing import List

from src.graph import build_tree
from src.mermaid import to_mermaid
from src.report import format_ascii_tree
from src.svg import render_svg

TREE = {
    "ROOT": ["LEFT", "RIGHT"],
    "LEFT": ["BASE"],
    "RIGHT": [],
    "BASE": [],
}


async def children(name: str) -> List[str]:
    """Отдаёт детей тестового дерева ROOT → LEFT, RIGHT; LEFT → BASE."""
    return TREE[name]


class AsciiTreeTest(unittest.TestCase):
    """Проверяет ASCII-дерево с ветками."""

    def test_branches(self) -> None:
        """Последний ребёнок помечен └──, остальные — ├──."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        self.assertEqual(format_ascii_tree(root), [
            "ROOT",
            "├── LEFT",
            "│   └── BASE",
            "└── RIGHT",
        ])

    def test_single_node(self) -> None:
        """Один узел — одна строка без веток."""
        root = asyncio.run(build_tree(children, "RIGHT", 3))
        self.assertEqual(format_ascii_tree(root), ["RIGHT"])


class MermaidTest(unittest.TestCase):
    """Проверяет диаграмму Mermaid."""

    def test_header_and_edges(self) -> None:
        """Заголовок graph TD и все рёбра на месте."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        lines = to_mermaid(root)
        self.assertEqual(lines[0], "graph TD")
        edges = [line for line in lines if "-->" in line]
        self.assertEqual(len(edges), 3)

    def test_labels_are_quoted(self) -> None:
        """Подписи узлов стоят в кавычках, идентификаторы свои."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        text = "\n".join(to_mermaid(root))
        self.assertIn('n0["ROOT"]', text)
        self.assertIn("n0 --> n1", text)


class SvgTest(unittest.TestCase):
    """Проверяет SVG-изображение."""

    def test_valid_xml(self) -> None:
        """SVG разбирается как XML."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        parsed = fromstring(render_svg(root))
        self.assertTrue(parsed.tag.endswith("svg"))

    def test_all_names_inside(self) -> None:
        """Все имена пакетов попали в подписи."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        svg = render_svg(root)
        for name in ("ROOT", "LEFT", "RIGHT", "BASE"):
            self.assertIn(f">{name}</text>", svg)

    def test_box_count(self) -> None:
        """Рамок столько же, сколько узлов."""
        root = asyncio.run(build_tree(children, "ROOT", 5))
        self.assertEqual(render_svg(root).count("<rect x="), 4)

    def test_names_are_escaped(self) -> None:
        """Спецсимволы в имени экранируются."""
        async def no_children(name: str) -> List[str]:
            """У узла нет детей."""
            return []

        root = asyncio.run(build_tree(no_children, "A&B", 3))
        self.assertIn("A&amp;B", render_svg(root))
