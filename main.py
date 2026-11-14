"""Инструмент визуализации графа зависимостей пакетного менеджера.

Этап 1: минимальный прототип с конфигурацией. Программа разбирает параметры
командной строки, проверяет их и выводит все параметры в формате
ключ-значение. Сбор и анализ зависимостей начинается со следующего этапа.

Запуск: python main.py --package requests --repo https://pypi.org/pypi
"""

import sys
from typing import List, Optional, Sequence

from src.config import Config, ConfigError

EXIT_OK = 0
EXIT_INVALID_PARAMS = 2
ERROR_PREFIX = "ошибка: "


def print_params(lines: List[str]) -> None:
    """Печатает строки с параметрами запуска."""
    for line in lines:
        print(line)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Разбирает параметры, печатает их и возвращает код выхода."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        config = Config.from_argv(args)
    except ConfigError as error:
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        return EXIT_INVALID_PARAMS
    print_params(config.describe())
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
