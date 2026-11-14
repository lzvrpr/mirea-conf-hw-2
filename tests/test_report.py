"""Тесты отчёта о прямых зависимостях."""

import unittest

from src.requirement import parse_requirement
from src.report import NO_DEPENDENCIES, format_report

METADATA = {"info": {"version": "2.34.2"}}

REQUIREMENTS = [
    parse_requirement("urllib3<3,>=1.26"),
    parse_requirement("certifi>=2023.5.7"),
    parse_requirement('PySocks!=1.5.7,>=1.5.6; extra == "socks"'),
]


class ReportTest(unittest.TestCase):
    """Проверяет состав и порядок строк отчёта."""

    def test_header_order_and_total(self) -> None:
        """Зависимости идут по алфавиту, затем итоговая строка."""
        lines = format_report("requests", METADATA, REQUIREMENTS)
        self.assertEqual(lines, [
            "прямые зависимости пакета requests 2.34.2:",
            "  certifi (>=2023.5.7)",
            "  PySocks (!=1.5.7,>=1.5.6) [extra: socks]",
            "  urllib3 (<3,>=1.26)",
            "всего: 3, базовых: 2, из extras: 1",
        ])

    def test_no_dependencies(self) -> None:
        """Пустой список зависимостей даёт отдельное сообщение."""
        lines = format_report("requests", METADATA, [])
        self.assertEqual(lines[-1], NO_DEPENDENCIES)

    def test_unknown_version(self) -> None:
        """Без версии в метаданных отчёт всё равно строится."""
        lines = format_report("requests", {}, [])
        self.assertIn("версия неизвестна", lines[0])
