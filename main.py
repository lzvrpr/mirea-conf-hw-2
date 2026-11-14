"""Инструмент визуализации графа зависимостей пакетного менеджера.

Этап 2: сбор данных. Метаданные пакета загружаются асинхронно через
aiohttp, строки зависимостей разбираются и печатаются списком.

Запуск: python main.py --package requests --repo https://pypi.org/pypi
"""

import asyncio
import sys
from typing import Optional, Sequence

import aiohttp

from src.config import MODE_TEST, Config, ConfigError
from src.pypi import RepositoryError, fetch_metadata
from src.requirement import direct_dependencies
from src.report import format_report

EXIT_OK = 0
EXIT_INVALID_PARAMS = 2
EXIT_REPOSITORY_ERROR = 3
ERROR_PREFIX = "ошибка: "
TEST_MODE_NOTICE = ("режим test пока не собирает зависимости: файл "
                    "тестового репозитория начнёт разбираться на этапе 3")


async def collect(config: Config, session: aiohttp.ClientSession) -> int:
    """Печатает прямые зависимости пакета и возвращает код выхода."""
    url = config.repo
    if not url:
        print(f"{ERROR_PREFIX}URL репозитория не задан", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    try:
        metadata = await fetch_metadata(session, url, config.package)
    except RepositoryError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    requirements = direct_dependencies(metadata)
    for line in format_report(config.package, metadata, requirements):
        print(line)
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
        print(TEST_MODE_NOTICE)
        return EXIT_OK
    async with aiohttp.ClientSession() as session:
        return await collect(config, session)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запускает приложение и возвращает код выхода."""
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    sys.exit(main())
