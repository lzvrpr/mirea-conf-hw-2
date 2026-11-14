"""Загрузка тестового репозитория из файла.

Формат файла: одна строка — одно ребро «A B», пакет A зависит от пакета B.
Имена пакетов — большие латинские буквы, цифры, дефис и подчёркивание.
Строки, начинающиеся с решётки, и пустые строки пропускаются.
"""

import asyncio
import re
from pathlib import Path

from src.graph import DependencyError, DependencyGraph

PACKAGE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*$")
COMMENT_PREFIX = "#"
EDGE_PARTS = 2
EMPTY_REPOSITORY = "в файле нет ни одной зависимости"


class TestRepositoryError(DependencyError):
    """Ошибка чтения файла тестового репозитория."""


async def load_test_repository(path: str) -> DependencyGraph:
    """Читает файл тестового репозитория и строит граф зависимостей.

    Чтение файла уходит в отдельный поток через asyncio.to_thread, поэтому
    событийный цикл не блокируется.
    """
    try:
        text = await asyncio.to_thread(Path(path).read_text,
                                       encoding="utf-8")
    except OSError as error:
        raise TestRepositoryError(f"файл не читается: {path}: {error}")
    graph = DependencyGraph()
    for number, line in enumerate(text.splitlines(), 1):
        _add_line(graph, line, number)
    if not graph.names():
        raise TestRepositoryError(f"файл {path}: {EMPTY_REPOSITORY}")
    return graph


def _add_line(graph: DependencyGraph, line: str, number: int) -> None:
    """Разбирает одну строку файла и добавляет ребро в граф."""
    text = line.strip()
    if not text or text.startswith(COMMENT_PREFIX):
        return
    parts = text.split()
    if len(parts) != EDGE_PARTS:
        raise TestRepositoryError(
            f"строка {number}: нужно два пакета через пробел: {text!r}")
    for name in parts:
        _check_name(name, number)
    graph.add_edge(parts[0], parts[1])


def _check_name(name: str, number: int) -> None:
    """Проверяет, что имя пакета записано большими латинскими буквами."""
    if not PACKAGE_PATTERN.match(name):
        raise TestRepositoryError(
            f"строка {number}: недопустимое имя пакета {name!r}: "
            "нужны большие латинские буквы, цифры, дефис, подчёркивание")
