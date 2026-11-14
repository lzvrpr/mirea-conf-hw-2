"""Разбор строк зависимостей в формате PEP 508.

PyPI отдаёт прямые зависимости в поле requires_dist списком строк вида
"name[extras] (specifier); marker". Строки разбираются без сторонних
библиотек: нужны только имя, ограничение версии, extras и маркер окружения.
"""

import re
from typing import Any, Dict, List, Optional

REQUIREMENT_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"\s*(?:\[(?P<extras>[^\]]*)\])?"
    r"\s*(?:\((?P<parens>[^)]*)\))?"
    r"\s*(?P<specifier>[^;]*?)"
    r"\s*(?:;\s*(?P<marker>.*))?$"
)
EXTRA_PATTERN = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")
NAME_SEPARATOR = "-"
NAME_SEPARATORS = re.compile(r"[-_.]+")


def normalize_name(name: str) -> str:
    """Приводит имя пакета к сравнимому виду по PEP 503."""
    return NAME_SEPARATORS.sub(NAME_SEPARATOR, name).lower()


class Requirement:
    """Одна зависимость пакета."""

    def __init__(self, name: str, extras: List[str], specifier: str,
                 marker: Optional[str]) -> None:
        """Запоминает разобранные части строки зависимости."""
        self.name = name
        self.extras = extras
        self.specifier = specifier
        self.marker = marker

    @property
    def extra(self) -> Optional[str]:
        """Возвращает имя extra из маркера или None у базовой зависимости."""
        match = EXTRA_PATTERN.search(self.marker or "")
        return match.group(1) if match else None

    def describe(self) -> str:
        """Возвращает строку для вывода: имя, ограничение и пометки."""
        parts = [self.name]
        if self.specifier:
            parts.append(f"({self.specifier})")
        if self.extra:
            parts.append(f"[extra: {self.extra}]")
        elif self.marker:
            parts.append(f"[маркер: {self.marker}]")
        return " ".join(parts)


def parse_requirement(line: str) -> Requirement:
    """Разбирает одну строку requires_dist в объект Requirement."""
    match = REQUIREMENT_PATTERN.match(line)
    if not match:
        raise ValueError(f"не разобрана строка зависимости: {line!r}")
    parens = match.group("parens") or ""
    plain = match.group("specifier") or ""
    specifier = (parens or plain).strip()
    marker = (match.group("marker") or "").strip() or None
    return Requirement(match.group("name"),
                       _split_extras(match.group("extras")), specifier, marker)


def direct_dependencies(metadata: Dict[str, Any]) -> List[Requirement]:
    """Возвращает прямые зависимости пакета из метаданных PyPI."""
    info = metadata.get("info") or {}
    lines = info.get("requires_dist") or []
    return [parse_requirement(line) for line in lines]


def _split_extras(raw: Optional[str]) -> List[str]:
    """Разбирает список extras в квадратных скобках."""
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]
