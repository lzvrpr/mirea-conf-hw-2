"""Тесты загрузки тестового репозитория из файла."""

import tempfile
import unittest
from pathlib import Path

from src.test_repo import TestRepositoryError, load_test_repository

LINEAR = "A B\nB C\nC D\n"


class TestRepositoryTestCase(unittest.IsolatedAsyncioTestCase):
    """Готовит временный файл тестового репозитория."""

    def _prepare(self) -> None:
        """Создаёт временный каталог."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def write_repo(self, text: str, name: str = "repo.txt") -> str:
        """Записывает текст в файл репозитория и возвращает путь."""
        path = Path(self.temp_dir.name) / name
        path.write_text(text, encoding="utf-8")
        return str(path)


class LoadTest(TestRepositoryTestCase):
    """Проверяет разбор корректных файлов."""

    async def test_edges(self) -> None:
        """Рёбра читаются в граф в порядке строк."""
        self._prepare()
        graph = await load_test_repository(self.write_repo(LINEAR))
        self.assertEqual(graph.children("A"), ["B"])
        self.assertEqual(graph.children("C"), ["D"])
        self.assertEqual(graph.names(), ["A", "B", "C", "D"])

    async def test_comments_and_blank_lines(self) -> None:
        """Комментарии и пустые строки пропускаются."""
        self._prepare()
        text = "# комментарий\n\nA B\n\n   \nB C\n"
        graph = await load_test_repository(self.write_repo(text))
        self.assertEqual(graph.children("A"), ["B"])

    async def test_duplicate_edge(self) -> None:
        """Повторное ребро не дублируется."""
        self._prepare()
        graph = await load_test_repository(self.write_repo("A B\nA B\n"))
        self.assertEqual(graph.children("A"), ["B"])


class ErrorsTest(TestRepositoryTestCase):
    """Проверяет обработку ошибок файла."""

    async def test_missing_file(self) -> None:
        """Несуществующий файл даёт ошибку."""
        self._prepare()
        missing = str(Path(self.temp_dir.name) / "nope.txt")
        with self.assertRaises(TestRepositoryError):
            await load_test_repository(missing)

    async def test_empty_file(self) -> None:
        """Файл без зависимостей даёт ошибку."""
        self._prepare()
        with self.assertRaises(TestRepositoryError):
            await load_test_repository(
                self.write_repo("# только комментарий\n"))

    async def test_one_name_in_line(self) -> None:
        """Строка с одним именем даёт ошибку с номером строки."""
        self._prepare()
        with self.assertRaises(TestRepositoryError) as caught:
            await load_test_repository(self.write_repo("A B\nB\n"))
        self.assertIn("строка 2", str(caught.exception))

    async def test_lowercase_name(self) -> None:
        """Имя строчными буквами даёт ошибку."""
        self._prepare()
        with self.assertRaises(TestRepositoryError) as caught:
            await load_test_repository(self.write_repo("a B\n"))
        self.assertIn("недопустимое имя", str(caught.exception))

    async def test_digits_allowed(self) -> None:
        """Цифры, дефис и подчёркивание в имени допустимы."""
        self._prepare()
        graph = await load_test_repository(self.write_repo("A_1 B-2\n"))
        self.assertEqual(graph.children("A_1"), ["B-2"])
