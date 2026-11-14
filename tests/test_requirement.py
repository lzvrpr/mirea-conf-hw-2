"""Тесты разбора строк зависимостей формата PEP 508."""

import unittest

from src.requirement import (direct_dependencies, normalize_name,
                             parse_requirement)


class ParseTest(unittest.TestCase):
    """Проверяет разбор отдельных строк requires_dist."""

    def test_plain_name(self) -> None:
        """Имя без ограничения разбирается целиком."""
        parsed = parse_requirement("requests")
        self.assertEqual(parsed.name, "requests")
        self.assertEqual(parsed.specifier, "")
        self.assertEqual(parsed.extras, [])
        self.assertIsNone(parsed.marker)

    def test_specifier(self) -> None:
        """Ограничение версии отделяется от имени."""
        parsed = parse_requirement("charset_normalizer<4,>=2")
        self.assertEqual(parsed.name, "charset_normalizer")
        self.assertEqual(parsed.specifier, "<4,>=2")

    def test_parens_specifier(self) -> None:
        """Ограничение в скобках тоже разбирается."""
        parsed = parse_requirement("foo (>=1.0,<2)")
        self.assertEqual(parsed.name, "foo")
        self.assertEqual(parsed.specifier, ">=1.0,<2")

    def test_extras(self) -> None:
        """Список extras попадает в поле extras."""
        parsed = parse_requirement("foo[bar, baz] (>=1.0)")
        self.assertEqual(parsed.extras, ["bar", "baz"])
        self.assertEqual(parsed.specifier, ">=1.0")

    def test_extra_marker(self) -> None:
        """Маркер extra == ... распознаётся как extra."""
        parsed = parse_requirement('PySocks!=1.5.7,>=1.5.6; extra == "socks"')
        self.assertEqual(parsed.extra, "socks")
        self.assertEqual(parsed.specifier, "!=1.5.7,>=1.5.6")

    def test_python_marker(self) -> None:
        """Маркер версии Python не считается extra."""
        parsed = parse_requirement('foo>=1.0; python_version < "3.8"')
        self.assertIsNone(parsed.extra)
        self.assertEqual(parsed.marker, 'python_version < "3.8"')

    def test_describe_extra(self) -> None:
        """В описании extra показан отдельной пометкой."""
        parsed = parse_requirement('PySocks!=1.5.7,>=1.5.6; extra == "socks"')
        self.assertEqual(parsed.describe(),
                         "PySocks (!=1.5.7,>=1.5.6) [extra: socks]")

    def test_describe_marker(self) -> None:
        """Маркер без extra показан как маркер окружения."""
        parsed = parse_requirement('foo; python_version < "3.8"')
        self.assertEqual(parsed.describe(),
                         'foo [маркер: python_version < "3.8"]')

    def test_empty_line(self) -> None:
        """Пустая строка не разбирается."""
        with self.assertRaises(ValueError):
            parse_requirement("")

    def test_garbage(self) -> None:
        """Строка без имени пакета не разбирается."""
        with self.assertRaises(ValueError):
            parse_requirement("=== 1.0")


class NormalizeTest(unittest.TestCase):
    """Проверяет приведение имени пакета к сравнимому виду."""

    def test_underscore_and_case(self) -> None:
        """Подчёркивание и регистр приводятся к дефису и нижнему регистру."""
        self.assertEqual(normalize_name("Charset_Normalizer"),
                         "charset-normalizer")

    def test_dots(self) -> None:
        """Точки тоже считаются разделителем."""
        self.assertEqual(normalize_name("zope.interface"),
                         "zope-interface")


class DirectDependenciesTest(unittest.TestCase):
    """Проверяет извлечение зависимостей из метаданных."""

    def test_all_requirements(self) -> None:
        """Все строки requires_dist превращаются в зависимости."""
        metadata = {"info": {"requires_dist": ["a", "b>=1.0"]}}
        parsed = direct_dependencies(metadata)
        self.assertEqual([item.name for item in parsed], ["a", "b"])

    def test_no_requirements(self) -> None:
        """Без requires_dist зависимостей нет."""
        self.assertEqual(direct_dependencies({"info": {}}), [])

    def test_no_info(self) -> None:
        """Метаданные без блока info не падают."""
        self.assertEqual(direct_dependencies({}), [])
