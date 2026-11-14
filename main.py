"""Инструмент визуализации графа зависимостей пакетного менеджера.

Этап 5: визуализация. Сеть и чтение файлов асинхронные: метаданные пакетов
запрашиваются через aiohttp, дети одного узла строятся параллельно через
asyncio.gather, файлы читаются и пишутся в отдельном потоке.

Запуск: python main.py --package requests --repo https://pypi.org/pypi
"""

import asyncio
import sys
from typing import Awaitable, Callable, List, Optional, Sequence

import aiohttp

from src.config import MODE_TEST, Config, ConfigError
from src.graph import Node, build_tree
from src.mermaid import to_mermaid
from src.pypi import PyPiProvider
from src.report import format_ascii_tree, format_summary, format_tree
from src.svg import render_svg
from src.test_repo import TestRepositoryError, load_test_repository

EXIT_OK = 0
EXIT_INVALID_PARAMS = 2
EXIT_REPOSITORY_ERROR = 3
ERROR_PREFIX = "ошибка: "
REVERSE_ONLY_TEST = ("обратные зависимости строятся только по тестовому "
                     "репозиторию: у репозитория PyPI нет обратного индекса")

Provider = Callable[[str], Awaitable[List[str]]]


def _real_provider(config: Config,
                   session: aiohttp.ClientSession) -> Provider:
    """Создаёт источник зависимостей из репозитория PyPI."""
    url = config.repo
    if not url:
        raise ConfigError("URL репозитория не задан")
    return PyPiProvider(session, url)


async def _test_provider(config: Config) -> Provider:
    """Создаёт источник зависимостей из файла тестового репозитория."""
    path = config.repo_file
    if not path:
        raise ConfigError("файл тестового репозитория не задан")
    graph = await load_test_repository(path)
    known = set(graph.names())

    async def children(name: str) -> List[str]:
        """Возвращает зависимости пакета из тестового репозитория."""
        if name not in known:
            raise TestRepositoryError(
                f"пакета {name!r} нет в тестовом репозитории")
        return graph.children(name)

    return children


async def build_provider(config: Config,
                         session: Optional[aiohttp.ClientSession]
                         ) -> Provider:
    """Выбирает источник зависимостей по режиму работы."""
    if config.mode == MODE_TEST:
        return await _test_provider(config)
    if session is None:
        raise ConfigError("для режима real нужна HTTP-сессия")
    return _real_provider(config, session)


def print_graph(config: Config, root: Node, title: str) -> None:
    """Печатает дерево зависимостей, сводку и диаграмму Mermaid."""
    print(f"{title} {root.name}, глубина до {config.depth}:")
    lines = format_ascii_tree(root) if config.tree else format_tree(root)
    for line in lines:
        print(line)
    for line in format_summary(root):
        print(line)
    if config.mermaid:
        print()
        print("диаграмма Mermaid:")
        for line in to_mermaid(root):
            print(line)


def _write_text(path: str, text: str) -> None:
    """Записывает текст в файл в кодировке UTF-8."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


async def save_image(config: Config, root: Node) -> int:
    """Сохраняет SVG-изображение графа и возвращает код выхода."""
    path = config.image
    if not path:
        return EXIT_OK
    try:
        await asyncio.to_thread(_write_text, path, render_svg(root))
    except OSError as error:
        print(f"{ERROR_PREFIX}изображение не сохранено: {error}",
              file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    print(f"изображение графа: {path}")
    return EXIT_OK


async def run_forward(config: Config,
                      session: Optional[aiohttp.ClientSession]) -> int:
    """Печатает дерево зависимостей пакета и возвращает код выхода."""
    try:
        provider = await build_provider(config, session)
    except ConfigError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    except TestRepositoryError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    root = await build_tree(provider, config.package, config.depth)
    if root.failed:
        print(f"{ERROR_PREFIX}{root.error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    print_graph(config, root, "дерево зависимостей пакета")
    return await save_image(config, root)


async def run_reverse(config: Config) -> int:
    """Печатает обратные зависимости пакета и возвращает код выхода."""
    if config.mode != MODE_TEST:
        print(f"{ERROR_PREFIX}{REVERSE_ONLY_TEST}", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    path = config.repo_file
    if not path:
        print(f"{ERROR_PREFIX}файл тестового репозитория не задан",
              file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    try:
        graph = await load_test_repository(path)
    except TestRepositoryError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    if config.package not in graph.names():
        print(f"{ERROR_PREFIX}пакета {config.package!r} нет в тестовом "
              "репозитории", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR

    async def parents(name: str) -> List[str]:
        """Возвращает пакеты, которые зависят от заданного."""
        return graph.parents(name)

    root = await build_tree(parents, config.package, config.depth)
    print_graph(config, root, "обратные зависимости пакета")
    return await save_image(config, root)


async def main_async(argv: Optional[Sequence[str]] = None) -> int:
    """Выполняет работу в одном событийном цикле."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        config = Config.from_argv(args)
    except ConfigError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    if config.reverse:
        return await run_reverse(config)
    if config.mode == MODE_TEST:
        return await run_forward(config, None)
    async with aiohttp.ClientSession() as session:
        return await run_forward(config, session)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запускает приложение и возвращает код выхода."""
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    sys.exit(main())
