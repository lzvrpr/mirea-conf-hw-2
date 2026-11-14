"""Параметры командной строки инструмента визуализации зависимостей.

Имя пакета, источник зависимостей (URL-адрес репозитория или файл тестового
репозитория), режим работы с тестовым репозиторием, режим вывода деревом,
максимальная глубина анализа и режим обратных зависимостей задаются опциями
командной строки. Каждый параметр проверяется.
"""

import argparse
import re
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import urlparse

PROGRAM_NAME = "dependency-graph"
PURPOSE = "визуализация графа зависимостей пакетного менеджера"

NOT_SET = "не задан"
YES = "да"
NO = "нет"

PACKAGE_HELP = "имя анализируемого пакета"
REPO_HELP = "URL-адрес репозитория пакетов"
REPO_FILE_HELP = "путь к файлу тестового репозитория"
MODE_HELP = "режим работы с тестовым репозиторием"
TREE_HELP = "выводить зависимости в виде ASCII-дерева"
DEPTH_HELP = "максимальная глубина анализа зависимостей"
REVERSE_HELP = "вывести обратные зависимости: кто зависит от пакета"

MODE_REAL = "real"
MODE_TEST = "test"
MODES = (MODE_REAL, MODE_TEST)

URL_SCHEMES = ("http", "https")

PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")

MIN_DEPTH = 1
MAX_DEPTH = 20
DEFAULT_DEPTH = 3


class ConfigError(Exception):
    """Ошибка в значении параметра командной строки."""


class Config:
    """Проверенные параметры запуска инструмента."""

    def __init__(self, package: str, repo: Optional[str],
                 repo_file: Optional[str], mode: str, tree: bool,
                 depth: int, reverse: bool = False) -> None:
        """Запоминает проверенные значения параметров."""
        self.package = package
        self.repo = repo
        self.repo_file = repo_file
        self.mode = mode
        self.tree = tree
        self.depth = depth
        self.reverse = reverse

    def describe(self) -> List[str]:
        """Возвращает все параметры в формате ключ-значение."""
        return [
            f"пакет: {self.package}",
            f"режим: {self.mode}",
            f"URL репозитория: {self.repo or NOT_SET}",
            f"файл тестового репозитория: {self.repo_file or NOT_SET}",
            f"вывод деревом: {YES if self.tree else NO}",
            f"максимальная глубина: {self.depth}",
            f"обратные зависимости: {YES if self.reverse else NO}",
        ]

    @staticmethod
    def from_argv(argv: Sequence[str]) -> "Config":
        """Разбирает параметры командной строки и проверяет их значения."""
        args = _parse_argv(argv)
        package = _check_package(args.package)
        depth = _check_depth(args.depth)
        if args.mode == MODE_TEST:
            repo = None
            repo_file = _check_test_source(args.repo, args.repo_file)
        else:
            repo = _check_real_source(args.repo, args.repo_file)
            repo_file = None
        return Config(package, repo, repo_file, args.mode, args.tree, depth,
                      args.reverse)


def _parse_argv(argv: Sequence[str]) -> argparse.Namespace:
    """Разбирает аргументы командной строки без проверки значений."""
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME, description=PURPOSE)
    parser.add_argument("--package", required=True, help=PACKAGE_HELP)
    parser.add_argument("--repo", help=REPO_HELP)
    parser.add_argument("--repo-file", dest="repo_file", help=REPO_FILE_HELP)
    parser.add_argument("--mode", choices=MODES, default=MODE_REAL,
                        help=MODE_HELP)
    parser.add_argument("--tree", action="store_true", help=TREE_HELP)
    parser.add_argument("--depth", type=int, default=DEFAULT_DEPTH,
                        help=DEPTH_HELP)
    parser.add_argument("--reverse", action="store_true", help=REVERSE_HELP)
    return parser.parse_args(list(argv))


def _check_package(package: str) -> str:
    """Проверяет имя пакета по правилам PEP 508.

    Допустимы латинские буквы, цифры, точка, дефис и подчёркивание;
    имя начинается и заканчивается буквой или цифрой.
    """
    name = package.strip()
    if not name:
        raise ConfigError("имя пакета не может быть пустым")
    if not PACKAGE_PATTERN.match(name):
        reason = ("допустимы латинские буквы, цифры, точка, дефис "
                  "и подчёркивание")
        raise ConfigError(f"недопустимое имя пакета {package!r}: {reason}")
    return name


def _check_depth(depth: int) -> int:
    """Проверяет, что глубина анализа лежит в допустимых пределах."""
    if depth < MIN_DEPTH:
        raise ConfigError(
            f"глубина анализа не может быть меньше {MIN_DEPTH}: {depth}")
    if depth > MAX_DEPTH:
        raise ConfigError(
            f"глубина анализа не может быть больше {MAX_DEPTH}: {depth}")
    return depth


def _check_repo(url: str) -> str:
    """Проверяет URL-адрес репозитория пакетов."""
    parsed = urlparse(url)
    if parsed.scheme not in URL_SCHEMES:
        raise ConfigError(
            f"URL репозитория {url!r} должен начинаться с http:// "
            "или https://")
    if not parsed.netloc:
        raise ConfigError(f"в URL репозитория {url!r} нет имени хоста")
    return url


def _check_repo_file(path: str) -> str:
    """Проверяет, что файл тестового репозитория существует и читается."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ConfigError(f"файл тестового репозитория не найден: {path}")
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            handle.read(1)
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(
            f"файл тестового репозитория не читается: {path}: {error}")
    return str(candidate)


def _check_test_source(repo: Optional[str],
                       repo_file: Optional[str]) -> str:
    """Проверяет источник данных в режиме тестового репозитория."""
    if repo:
        raise ConfigError(
            "в режиме test задан --repo: используйте только --repo-file")
    if not repo_file:
        raise ConfigError("в режиме test нужен --repo-file")
    return _check_repo_file(repo_file)


def _check_real_source(repo: Optional[str],
                       repo_file: Optional[str]) -> str:
    """Проверяет источник данных в режиме реального репозитория."""
    if repo_file:
        raise ConfigError(
            "в режиме real задан --repo-file: используйте только --repo")
    if not repo:
        raise ConfigError("в режиме real нужен --repo")
    return _check_repo(repo)
