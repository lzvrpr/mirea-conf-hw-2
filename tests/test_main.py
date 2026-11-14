"""Интеграционные тесты запуска приложения."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from typing import Tuple

from main import (EXIT_INVALID_PARAMS, EXIT_OK, EXIT_REPOSITORY_ERROR,
                  main)

BRANCHING = ("ROOT LEFT\n"
             "ROOT RIGHT\n"
             "LEFT SHARED\n"
             "RIGHT SHARED\n"
             "SHARED BASE\n")


class MainTestCase(unittest.TestCase):
    """Готовит временный тестовый репозиторий и запускает main."""

    def _prepare(self) -> None:
        """Записывает файл тестового репозитория во временный каталог."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "repo.txt"
        self.path.write_text(BRANCHING, encoding="utf-8")

    def run_main(self, *args: str) -> Tuple[int, str]:
        """Запускает main и возвращает код выхода и stdout."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def run_main_stderr(self, *args: str) -> Tuple[int, str]:
        """Запускает main и возвращает код выхода и stderr."""
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = main(list(args))
        return code, errors.getvalue()


class ForwardTest(MainTestCase):
    """Проверяет прямой обход через main."""

    def test_tree(self) -> None:
        """Дерево от корня содержит обе ветки."""
        self._prepare()
        code, output = self.run_main("--package", "ROOT", "--mode", "test",
                                     "--repo-file", str(self.path))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("дерево зависимостей пакета ROOT", output)
        self.assertIn("LEFT", output)
        self.assertIn("RIGHT", output)

    def test_ascii_tree(self) -> None:
        """С флагом --tree ветки печатаются символами ├── и └──."""
        self._prepare()
        code, output = self.run_main("--package", "ROOT", "--mode", "test",
                                     "--repo-file", str(self.path), "--tree")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("├── LEFT", output)
        self.assertIn("└── RIGHT", output)

    def test_mermaid(self) -> None:
        """С флагом --mermaid печатается текст диаграммы."""
        self._prepare()
        code, output = self.run_main("--package", "ROOT", "--mode", "test",
                                     "--repo-file", str(self.path),
                                     "--mermaid")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("graph TD", output)
        self.assertIn("-->", output)

    def test_image(self) -> None:
        """С флагом --image создаётся SVG-файл."""
        self._prepare()
        target = Path(self.temp_dir.name) / "graph.svg"
        code, output = self.run_main("--package", "ROOT", "--mode", "test",
                                     "--repo-file", str(self.path),
                                     "--image", str(target))
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(target.is_file())
        self.assertIn("<svg", target.read_text(encoding="utf-8"))
        self.assertIn("изображение графа", output)


class ReverseTest(MainTestCase):
    """Проверяет обратный обход через main."""

    def test_direct_parents(self) -> None:
        """Обратные зависимости пакета SHARED — LEFT и RIGHT."""
        self._prepare()
        code, output = self.run_main("--package", "SHARED", "--mode", "test",
                                     "--repo-file", str(self.path),
                                     "--reverse", "--depth", "1")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("обратные зависимости пакета SHARED", output)
        self.assertIn("LEFT", output)
        self.assertIn("RIGHT", output)

    def test_chain_up(self) -> None:
        """С глубиной 3 обратный обход доходит до корня."""
        self._prepare()
        code, output = self.run_main("--package", "SHARED", "--mode", "test",
                                     "--repo-file", str(self.path),
                                     "--reverse", "--depth", "3")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("ROOT", output)
        self.assertIn("узлов: 5", output)

    def test_unknown_package(self) -> None:
        """Неизвестный пакет даёт ошибку."""
        self._prepare()
        code, errors = self.run_main_stderr(
            "--package", "ZZZ", "--mode", "test",
            "--repo-file", str(self.path), "--reverse")
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("ZZZ", errors)

    def test_real_mode_rejected(self) -> None:
        """В режиме real обратные зависимости не строятся."""
        self._prepare()
        code, errors = self.run_main_stderr(
            "--package", "requests", "--repo", "https://pypi.org/pypi",
            "--reverse")
        self.assertEqual(code, EXIT_INVALID_PARAMS)
        self.assertIn("обратные зависимости", errors)
