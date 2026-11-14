"""Граф зависимостей и асинхронный обход в глубину.

Узел дерева хранит имя пакета, детей и пометки: цикл (имя уже встречалось
выше по пути), обрезка по максимальной глубине, ошибка получения
зависимостей. Дети одного узла запрашиваются параллельно.
"""

import asyncio
from typing import (Awaitable, Callable, Dict, Iterable, List, Optional,
                    Sequence, Tuple)

ChildrenOf = Callable[[str], Awaitable[Sequence[str]]]


class DependencyError(Exception):
    """Ошибка получения зависимостей пакета."""


class Node:
    """Узел дерева зависимостей."""

    def __init__(self, name: str) -> None:
        """Создаёт узел без детей и без пометок."""
        self.name = name
        self.children: List["Node"] = []
        self.cycle = False
        self.truncated = False
        self.failed = False
        self.error: Optional[str] = None

    def walk(self) -> Iterable["Node"]:
        """Обходит узел и всех его потомков в глубину."""
        yield self
        for child in self.children:
            yield from child.walk()


class DependencyGraph:
    """Направленный граф «пакет зависит от пакета»."""

    def __init__(self) -> None:
        """Создаёт пустой граф."""
        self._edges: Dict[str, List[str]] = {}

    def add_edge(self, parent: str, child: str) -> None:
        """Добавляет ребро parent → child, повторное ребро не дублируется."""
        self._edges.setdefault(parent, [])
        self._edges.setdefault(child, [])
        if child not in self._edges[parent]:
            self._edges[parent].append(child)

    def children(self, name: str) -> List[str]:
        """Возвращает прямые зависимости пакета."""
        return list(self._edges.get(name, []))

    def parents(self, name: str) -> List[str]:
        """Возвращает пакеты, которые зависят от заданного, по алфавиту."""
        return sorted(parent for parent, kids in self._edges.items()
                      if name in kids)

    def names(self) -> List[str]:
        """Возвращает все имена пакетов графа по алфавиту."""
        return sorted(self._edges)


async def build_tree(children_of: ChildrenOf, name: str, max_depth: int,
                     depth: int = 0,
                     path: Tuple[str, ...] = ()) -> Node:
    """Строит дерево зависимостей обходом в глубину с рекурсией.

    path — имена пакетов от корня до текущего узла: если имя уже встречалось,
    это цикл, и узел дальше не раскрывается. Дети одного узла запрашиваются
    параллельно через asyncio.gather.
    """
    node = Node(name)
    if name in path:
        node.cycle = True
        return node
    if depth >= max_depth:
        node.truncated = True
        return node
    try:
        names = await children_of(name)
    except DependencyError as error:
        node.failed = True
        node.error = str(error)
        return node
    inner_path = path + (name,)
    tasks = [build_tree(children_of, child, max_depth, depth + 1, inner_path)
             for child in names]
    if tasks:
        node.children = list(await asyncio.gather(*tasks))
    return node
