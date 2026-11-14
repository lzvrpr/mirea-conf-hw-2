"""Инструмент визуализации графа зависимостей пакетного менеджера.

Этап 3: основные операции. Граф строится асинхронным обходом в глубину,
дети одного узла запрашиваются параллельно через asyncio.gather.

Запуск: python main.py --package requests --repo https://pypi.org/pypi
"""

import asyncio
import sys
from typing import Awaitable, Callable, List, Optional, Sequence

import aiohttp

from src.config import MODE_TEST, Config, ConfigError
from src.graph import Node, build_tree
from src.pypi import PyPiProvider
from src.report import format_summary, format_tree
from src.test_repo import TestRepositoryError, load_test_repository

EXIT_OK = 0
EXIT_INVALID_PARAMS = 2
EXIT_REPOSITORY_ERROR = 3
ERROR_PREFIX = "ошибка: "

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


def print_tree(config: Config, root: Node, title: str) -> None:
    """Печатает заголовок, дерево зависимостей и сводку."""
    print(f"{title} {root.name}, глубина до {config.depth}:")
    for line in format_tree(root):
        print(line)
    for line in format_summary(root):
        print(line)


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
    print_tree(config, root, "дерево зависимостей пакета")
    return EXIT_OK


async def main_async(argv: Optional[Sequence[str]] = None) -> int:
    """Выполняет работу в одном событийном цикле."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        config = Config.from_argv(args)
    except ConfigError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    if config.mode == MODE_TEST:
        return await run_forward(config, None)
    async with aiohttp.ClientSession() as session:
        return await run_forward(config, session)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запускает приложение и возвращает код выхода."""
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    sys.exit(main())
