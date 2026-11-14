"""Печать прямых зависимостей пакета."""

from typing import Any, Dict, List

from src.requirement import Requirement

NO_DEPENDENCIES = "прямых зависимостей нет."
TOTAL = "всего: {total}, базовых: {base}, из extras: {extra}"
INDENT = "  "
UNKNOWN_VERSION = "версия неизвестна"


def _sort_key(requirement: Requirement) -> str:
    """Ключ сортировки зависимостей: имя в нижнем регистре."""
    return requirement.name.lower()


def format_report(package: str, metadata: Dict[str, Any],
                  requirements: List[Requirement]) -> List[str]:
    """Возвращает строки отчёта о прямых зависимостях пакета."""
    info = metadata.get("info") or {}
    version = info.get("version") or UNKNOWN_VERSION
    lines = [f"прямые зависимости пакета {package} {version}:"]
    if not requirements:
        lines.append(NO_DEPENDENCIES)
        return lines
    for requirement in sorted(requirements, key=_sort_key):
        lines.append(f"{INDENT}{requirement.describe()}")
    base = [item for item in requirements if not item.extra]
    lines.append(TOTAL.format(total=len(requirements), base=len(base),
                              extra=len(requirements) - len(base)))
    return lines
