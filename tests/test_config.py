"""Тесты разбора и проверки параметров командной строки."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.config import (DEFAULT_DEPTH, MAX_DEPTH, MIN_DEPTH, MODE_REAL,
                        MODE_TEST, NO, NOT_SET, YES, Config, ConfigError)

GOOD_REPO = "https://pypi.org/pypi"
REPO_TEXT = "A B\n"


class ConfigTestCase(unittest.TestCase):
    """Готовит временный файл тестового репозитория для проверок."""

    def _prepare(self) -> None:
        """Создаёт временный каталог с файлом тестового репозитория."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo_file = Path(self.temp_dir.name) / "repo.txt"
        self.repo_file.write_text(REPO_TEXT, encoding="utf-8")

    def build(self, *args: str) -> Config:
        """Разбирает переданные аргументы и возвращает параметры."""
        return Config.from_argv(list(args))

    def assert_config_error(self, *args: str) -> None:
        """Проверяет, что параметры отвергаются с ConfigError."""
        with self.assertRaises(ConfigError):
            self.build(*args)

    def assert_argparse_error(self, *args: str) -> None:
        """Проверяет, что argparse завершает разбор с ошибкой."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.build(*args)


class RealModeTest(ConfigTestCase):
    """Разбирает параметры в режиме реального репозитория."""

    def test_all_params(self) -> None:
        """Все заданные параметры попадают в свои поля."""
        self._prepare()
        config = self.build("--package", "requests", "--repo", GOOD_REPO,
                            "--mode", MODE_REAL, "--tree", "--depth", "4")
        self.assertEqual(config.package, "requests")
        self.assertEqual(config.repo, GOOD_REPO)
        self.assertIsNone(config.repo_file)
        self.assertEqual(config.mode, MODE_REAL)
        self.assertTrue(config.tree)
        self.assertEqual(config.depth, 4)

    def test_defaults(self) -> None:
        """Незаданные параметры получают значения по умолчанию."""
        self._prepare()
        config = self.build("--package", "requests", "--repo", GOOD_REPO)
        self.assertEqual(config.mode, MODE_REAL)
        self.assertFalse(config.tree)
        self.assertEqual(config.depth, DEFAULT_DEPTH)

    def test_package_is_stripped(self) -> None:
        """Пробелы вокруг имени пакета не считаются частью имени."""
        self._prepare()
        config = self.build("--package", "  requests  ", "--repo", GOOD_REPO)
        self.assertEqual(config.package, "requests")


class TestModeTest(ConfigTestCase):
    """Разбирает параметры в режиме тестового репозитория."""

    def test_repo_file(self) -> None:
        """Путь к файлу тестового репозитория попадает в своё поле."""
        self._prepare()
        config = self.build("--package", "A", "--mode", MODE_TEST,
                            "--repo-file", str(self.repo_file))
        self.assertEqual(config.mode, MODE_TEST)
        self.assertEqual(config.repo_file, str(self.repo_file))
        self.assertIsNone(config.repo)


class DescribeTest(ConfigTestCase):
    """Проверяет вывод параметров в формате ключ-значение."""

    def test_real_mode(self) -> None:
        """Все параметры выводятся в порядке ключ-значение."""
        self._prepare()
        config = self.build("--package", "requests", "--repo", GOOD_REPO,
                            "--depth", "2")
        self.assertEqual(config.describe(), [
            "пакет: requests",
            f"режим: {MODE_REAL}",
            f"URL репозитория: {GOOD_REPO}",
            f"файл тестового репозитория: {NOT_SET}",
            f"вывод деревом: {NO}",
            "максимальная глубина: 2",
        ])

    def test_tree_yes(self) -> None:
        """При флаге --tree режим вывода деревом печатается как «да»."""
        self._prepare()
        config = self.build("--package", "requests", "--repo", GOOD_REPO,
                            "--tree")
        self.assertIn(f"вывод деревом: {YES}", config.describe())


class PackageErrorTest(ConfigTestCase):
    """Проверяет ошибки в имени пакета."""

    def test_empty(self) -> None:
        """Пустое имя пакета отвергается."""
        self._prepare()
        self.assert_config_error("--package", "", "--repo", GOOD_REPO)

    def test_blank(self) -> None:
        """Имя из одних пробелов отвергается."""
        self._prepare()
        self.assert_config_error("--package", "   ", "--repo", GOOD_REPO)

    def test_bad_start(self) -> None:
        """Имя, начинающееся с дефиса, отвергается."""
        self._prepare()
        self.assert_config_error("--package=-requests", "--repo", GOOD_REPO)

    def test_bad_end(self) -> None:
        """Имя, заканчивающееся точкой, отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests.", "--repo", GOOD_REPO)

    def test_cyrillic(self) -> None:
        """Кириллица в имени пакета отвергается."""
        self._prepare()
        self.assert_config_error("--package", "пакет", "--repo", GOOD_REPO)

    def test_space_inside(self) -> None:
        """Пробел внутри имени пакета отвергается."""
        self._prepare()
        self.assert_config_error("--package", "re quests", "--repo", GOOD_REPO)

    def test_slash(self) -> None:
        """Косая черта в имени пакета отвергается."""
        self._prepare()
        self.assert_config_error("--package", "a/b", "--repo", GOOD_REPO)


class DepthErrorTest(ConfigTestCase):
    """Проверяет ошибки в максимальной глубине анализа."""

    def test_too_small(self) -> None:
        """Глубина меньше минимальной отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests", "--repo", GOOD_REPO,
                                 "--depth", str(MIN_DEPTH - 1))

    def test_too_big(self) -> None:
        """Глубина больше максимальной отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests", "--repo", GOOD_REPO,
                                 "--depth", str(MAX_DEPTH + 1))

    def test_not_a_number(self) -> None:
        """Нечисловая глубина завершает разбор с ошибкой."""
        self._prepare()
        self.assert_argparse_error("--package", "requests", "--repo", GOOD_REPO,
                                   "--depth", "много")


class RepoErrorTest(ConfigTestCase):
    """Проверяет ошибки в URL-адресе репозитория."""

    def test_no_scheme(self) -> None:
        """URL без схемы отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests",
                                 "--repo", "pypi.org/pypi")

    def test_wrong_scheme(self) -> None:
        """URL с посторонней схемой отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests",
                                 "--repo", "ftp://pypi.org/pypi")

    def test_no_host(self) -> None:
        """URL без имени хоста отвергается."""
        self._prepare()
        self.assert_config_error("--package", "requests",
                                 "--repo", "https://")


class RepoFileErrorTest(ConfigTestCase):
    """Проверяет ошибки в файле тестового репозитория."""

    def test_missing_file(self) -> None:
        """Несуществующий файл отвергается."""
        self._prepare()
        missing = Path(self.temp_dir.name) / "нет-такого.txt"
        self.assert_config_error("--package", "A", "--mode", MODE_TEST,
                                 "--repo-file", str(missing))

    def test_directory(self) -> None:
        """Каталог вместо файла отвергается."""
        self._prepare()
        self.assert_config_error("--package", "A", "--mode", MODE_TEST,
                                 "--repo-file", self.temp_dir.name)


class SourceErrorTest(ConfigTestCase):
    """Проверяет согласованность режима и источника данных."""

    def test_test_without_file(self) -> None:
        """В режиме test нужен --repo-file."""
        self._prepare()
        self.assert_config_error("--package", "A", "--mode", MODE_TEST)

    def test_test_with_repo(self) -> None:
        """В режиме test нельзя задавать --repo."""
        self._prepare()
        self.assert_config_error("--package", "A", "--mode", MODE_TEST,
                                 "--repo", GOOD_REPO,
                                 "--repo-file", str(self.repo_file))

    def test_real_without_repo(self) -> None:
        """В режиме real нужен --repo."""
        self._prepare()
        self.assert_config_error("--package", "A", "--mode", MODE_REAL)

    def test_real_with_file(self) -> None:
        """В режиме real нельзя задавать --repo-file."""
        self._prepare()
        self.assert_config_error("--package", "A", "--repo", GOOD_REPO,
                                 "--repo-file", str(self.repo_file))


class ArgParseTest(ConfigTestCase):
    """Проверяет ошибки разбора самих аргументов."""

    def test_no_package(self) -> None:
        """Без --package разбор завершается ошибкой."""
        self._prepare()
        self.assert_argparse_error("--repo", GOOD_REPO)

    def test_unknown_option(self) -> None:
        """Неизвестная опция завершает разбор с ошибкой."""
        self._prepare()
        self.assert_argparse_error("--package", "requests",
                                   "--repo", GOOD_REPO, "--unknown", "1")

    def test_bad_mode(self) -> None:
        """Недопустимый режим завершает разбор с ошибкой."""
        self._prepare()
        self.assert_argparse_error("--package", "requests",
                                   "--repo", GOOD_REPO, "--mode", "cloud")
