"""Диаграмма зависимостей на языке Mermaid.

Узлы получают короткие идентификаторы n0, n1, … — так имя пакета с дефисом
или точкой не ломает синтаксис диаграммы; само имя попадает в подпись.
"""

from typing import Dict, List

from src.graph import Node
from src.report import display_label

HEADER = "graph TD"
INDENT = "    "


def to_mermaid(root: Node) -> List[str]:
    """Возвращает текст диаграммы Mermaid для дерева зависимостей."""
    nodes = list(root.walk())
    ids: Dict[int, str] = {id(node): f"n{index}"
                           for index, node in enumerate(nodes)}
    lines = [HEADER]
    for node in nodes:
        lines.append(f"{INDENT}{ids[id(node)]}"
                     f'["{_label(node)}"]')
    for node in nodes:
        for child in node.children:
            lines.append(f"{INDENT}{ids[id(node)]} --> {ids[id(child)]}")
    return lines


def _label(node: Node) -> str:
    """Возвращает подпись узла без символов, ломающих синтаксис Mermaid."""
    return display_label(node).replace('"', "'")
