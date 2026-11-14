"""Печать зависимостей: плоский список и дерево обхода."""

from typing import Any, Dict, Iterator, List

from src.graph import Node
from src.requirement import Requirement

NO_DEPENDENCIES = "прямых зависимостей нет."
TOTAL = "всего: {total}, базовых: {base}, из extras: {extra}"
INDENT = "  "
UNKNOWN_VERSION = "версия неизвестна"

TREE_INDENT = "  "
CYCLE_MARK = " (цикл)"
FAILED_MARK = " (зависимости не получены)"
TRUNCATED_MARK = " (глубина)"
SUMMARY = ("узлов: {nodes}, циклов: {cycles}, "
           "с ошибкой: {failed}, обрезано по глубине: {truncated}")


def _sort_key(requirement: Requirement) -> str:
    """Ключ сортировки зависимостей: имя в нижнем регистре."""
    return requirement.name.lower()


def format_report(package: str, metadata: Dict[str, Any],
                  requirements: List[Requirement]) -> List[str]:
    """Возвращает строки отчёта о прямых зависимостях пакета."""
    info = metadata.get("info") or {}
    version = info.get("version") or UNKNOWN_VERSION
    lines = [f"прямые зависимости пакета {package} {version}:"]
    if not requirements:
        lines.append(NO_DEPENDENCIES)
        return lines
    for requirement in sorted(requirements, key=_sort_key):
        lines.append(f"{INDENT}{requirement.describe()}")
    base = [item for item in requirements if not item.extra]
    lines.append(TOTAL.format(total=len(requirements), base=len(base),
                              extra=len(requirements) - len(base)))
    return lines


def node_label(node: Node) -> str:
    """Возвращает имя узла с пометкой его состояния."""
    if node.cycle:
        return node.name + CYCLE_MARK
    if node.failed:
        return node.name + FAILED_MARK
    if node.truncated:
        return node.name + TRUNCATED_MARK
    return node.name


def display_label(node: Node) -> str:
    """Возвращает имя узла для диаграмм: цикл помечен, глубина — нет."""
    return node.name + CYCLE_MARK if node.cycle else node.name


def format_tree(root: Node) -> List[str]:
    """Возвращает строки дерева зависимостей с отступами по уровню."""
    return list(_tree_lines(root, 0))


def _tree_lines(node: Node, level: int) -> Iterator[str]:
    """Отдаёт строку узла и строки всех его потомков."""
    yield TREE_INDENT * level + node_label(node)
    for child in node.children:
        yield from _tree_lines(child, level + 1)


def format_summary(root: Node) -> List[str]:
    """Возвращает строку со сводкой по дереву зависимостей."""
    nodes = list(root.walk())
    return [SUMMARY.format(nodes=len(nodes),
                           cycles=sum(1 for node in nodes if node.cycle),
                           failed=sum(1 for node in nodes if node.failed),
                           truncated=sum(1 for node in nodes
                                         if node.truncated))]


ASCII_BRANCH = "├── "
ASCII_LAST = "└── "
ASCII_LINE = "│   "
ASCII_SPACE = "    "


def format_ascii_tree(root: Node) -> List[str]:
    """Возвращает дерево зависимостей в виде ASCII-дерева с ветками."""
    lines = [node_label(root)]
    _append_ascii(root, "", lines)
    return lines


def _append_ascii(node: Node, prefix: str, lines: List[str]) -> None:
    """Дописывает в список строки детей узла с префиксом ветки."""
    for index, child in enumerate(node.children):
        last = index == len(node.children) - 1
        branch = ASCII_LAST if last else ASCII_BRANCH
        lines.append(prefix + branch + node_label(child))
        extension = ASCII_SPACE if last else ASCII_LINE
        _append_ascii(child, prefix + extension, lines)
