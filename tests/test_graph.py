"""Тесты построения графа зависимостей и асинхронного обхода."""

import unittest
from typing import Dict, List

from src.graph import DependencyError, DependencyGraph, build_tree

SIMPLE: Dict[str, List[str]] = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": [],
}


async def simple_children(name: str) -> List[str]:
    """Отдаёт зависимости из словаря SIMPLE."""
    if name not in SIMPLE:
        raise DependencyError(f"нет пакета {name}")
    return SIMPLE[name]


class GraphTest(unittest.TestCase):
    """Проверяет хранение рёбер графа."""

    def test_edges_and_children(self) -> None:
        """Ребро попадает в список детей своего пакета."""
        graph = DependencyGraph()
        graph.add_edge("A", "B")
        self.assertEqual(graph.children("A"), ["B"])
        self.assertEqual(graph.children("B"), [])

    def test_duplicate_edge(self) -> None:
        """Повторное ребро не дублируется."""
        graph = DependencyGraph()
        graph.add_edge("A", "B")
        graph.add_edge("A", "B")
        self.assertEqual(graph.children("A"), ["B"])

    def test_names(self) -> None:
        """В списке имён есть все пакеты графа, по алфавиту."""
        graph = DependencyGraph()
        graph.add_edge("B", "A")
        self.assertEqual(graph.names(), ["A", "B"])

    def test_parents(self) -> None:
        """Обратные рёбра находят пакеты, которые зависят от заданного."""
        graph = DependencyGraph()
        graph.add_edge("A", "C")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        self.assertEqual(graph.parents("C"), ["A", "B"])
        self.assertEqual(graph.parents("A"), [])


class BuildTreeTest(unittest.IsolatedAsyncioTestCase):
    """Проверяет асинхронный обход в глубину."""

    async def test_root_and_children(self) -> None:
        """Корень и прямые дети попадают в дерево по порядку рёбер."""
        root = await build_tree(simple_children, "A", 5)
        self.assertEqual(root.name, "A")
        self.assertEqual([node.name for node in root.children], ["B", "C"])

    async def test_repeat_in_branches_is_not_cycle(self) -> None:
        """Пакет в двух ветках — обычное дерево, а не цикл."""
        root = await build_tree(simple_children, "A", 5)
        repeated = [node for node in root.walk() if node.name == "D"]
        self.assertEqual(len(repeated), 2)
        self.assertFalse(any(node.cycle for node in repeated))

    async def test_depth_limit(self) -> None:
        """На максимальной глубине дети не раскрываются."""
        root = await build_tree(simple_children, "A", 1)
        self.assertEqual([node.name for node in root.children], ["B", "C"])
        self.assertTrue(all(node.truncated for node in root.children))

    async def test_cycle_is_marked(self) -> None:
        """Имя, уже встречавшееся выше по пути, помечается циклом."""

        async def children(name: str) -> List[str]:
            """Отдаёт детей из словаря с циклом."""
            return {"A": ["B"], "B": ["A"]}[name]

        root = await build_tree(children, "A", 10)
        back_edge = root.children[0].children[0]
        self.assertEqual(back_edge.name, "A")
        self.assertTrue(back_edge.cycle)
        self.assertEqual(back_edge.children, [])

    async def test_missing_package(self) -> None:
        """Ошибка источника сохраняется в узле, обход не падает."""
        root = await build_tree(simple_children, "ZZZ", 3)
        self.assertTrue(root.failed)
        self.assertIn("ZZZ", root.error or "")

    async def test_walk_order(self) -> None:
        """Обход идёт в глубину: узел, потомки, затем следующий ребёнок."""
        root = await build_tree(simple_children, "A", 5)
        self.assertEqual([node.name for node in root.walk()],
                         ["A", "B", "D", "C", "D"])
