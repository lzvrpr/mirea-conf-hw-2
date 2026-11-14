"""Построение SVG-изображения дерева зависимостей.

Раскладка своя: каждый уровень дерева — строка, каждый лист занимает одну
колонку, родитель стоит над серединой своих детей. Сторонние библиотеки для
рисования не используются: SVG собирается как текст.
"""

from html import escape
from typing import Dict, List, Tuple

from src.graph import Node
from src.report import display_label

NODE_HEIGHT = 34
CHAR_WIDTH = 8
MIN_NODE_WIDTH = 110
NODE_PADDING = 26
H_GAP = 16
V_GAP = 64
MARGIN = 24
FONT_SIZE = 13
TEXT_OFFSET = NODE_HEIGHT / 2 + FONT_SIZE / 3

BACKGROUND = "#ffffff"
NODE_FILL = "#f7fafc"
NODE_STROKE = "#4a5568"
EDGE_STROKE = "#718096"
TEXT_FILL = "#1a202c"
FONT_FAMILY = "DejaVu Sans, sans-serif"

Position = Tuple[float, float]


def render_svg(root: Node) -> str:
    """Возвращает SVG-изображение дерева зависимостей."""
    width = _node_width(root)
    step = width + H_GAP
    columns = max(1, _leaf_count(root))
    rows = _depth(root) + 1
    canvas_width = columns * step + MARGIN * 2
    canvas_height = (rows - 1) * V_GAP + NODE_HEIGHT + MARGIN * 2
    positions: Dict[int, Position] = {}
    _assign(root, 0, MARGIN, step, positions)
    parts = [_svg_header(canvas_width, canvas_height),
             f'<rect width="100%" height="100%" fill="{BACKGROUND}"/>']
    parts.extend(_edges(root, positions))
    parts.extend(_boxes(root, positions, width))
    parts.append("</svg>")
    return "\n".join(parts)


def _node_width(root: Node) -> float:
    """Возвращает ширину рамки узла по самому длинному имени."""
    longest = max(len(display_label(node)) for node in root.walk())
    return max(MIN_NODE_WIDTH, longest * CHAR_WIDTH + NODE_PADDING)


def _leaf_count(node: Node) -> int:
    """Считает листья поддерева: каждый лист занимает одну колонку."""
    if not node.children:
        return 1
    return sum(_leaf_count(child) for child in node.children)


def _depth(node: Node) -> int:
    """Возвращает максимальную глубину поддерева от узла."""
    if not node.children:
        return 0
    return 1 + max(_depth(child) for child in node.children)


def _assign(node: Node, level: int, left: float, step: float,
            positions: Dict[int, Position]) -> float:
    """Расставляет узлы поддерева и возвращает его правую границу."""
    if not node.children:
        center = left + step / 2
        positions[id(node)] = (center, level)
        return left + step
    cursor = left
    centers = []
    for child in node.children:
        cursor = _assign(child, level + 1, cursor, step, positions)
        centers.append(positions[id(child)][0])
    center = (centers[0] + centers[-1]) / 2
    positions[id(node)] = (center, level)
    return cursor


def _edges(root: Node, positions: Dict[int, Position]) -> List[str]:
    """Возвращает SVG-элементы рёбер между узлами."""
    parts = []
    for node in root.walk():
        start_x, start_level = positions[id(node)]
        start_y = MARGIN + start_level * V_GAP + NODE_HEIGHT
        for child in node.children:
            end_x, end_level = positions[id(child)]
            end_y = MARGIN + end_level * V_GAP
            middle = (start_y + end_y) / 2
            points = (f"{start_x:.1f},{start_y:.1f} "
                      f"{start_x:.1f},{middle:.1f} "
                      f"{end_x:.1f},{middle:.1f} "
                      f"{end_x:.1f},{end_y:.1f}")
            parts.append(f'<polyline points="{points}" fill="none" '
                         f'stroke="{EDGE_STROKE}" stroke-width="1.5"/>')
    return parts


def _boxes(root: Node, positions: Dict[int, Position],
           width: float) -> List[str]:
    """Возвращает SVG-элементы рамок и подписей узлов."""
    parts = []
    for node in root.walk():
        center_x, level = positions[id(node)]
        top = MARGIN + level * V_GAP
        left = center_x - width / 2
        parts.append(
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" '
            f'height="{NODE_HEIGHT}" rx="6" fill="{NODE_FILL}" '
            f'stroke="{NODE_STROKE}"/>')
        parts.append(
            f'<text x="{center_x:.1f}" y="{top + TEXT_OFFSET:.1f}" '
            f'text-anchor="middle" font-family="{FONT_FAMILY}" '
            f'font-size="{FONT_SIZE}" fill="{TEXT_FILL}">'
            f'{escape(display_label(node))}</text>')
    return parts


def _svg_header(width: float, height: float) -> str:
    """Возвращает открывающий тег SVG с размерами."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {width:.0f} {height:.0f}">')
