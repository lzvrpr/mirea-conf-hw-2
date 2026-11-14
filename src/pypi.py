"""Загрузка метаданных пакета из репозитория PyPI.

Менеджеры пакетов и чужие библиотеки для получения зависимостей не
используются: запрос идёт через aiohttp, ответ разбирается стандартным json.
"""

import asyncio
import json
from typing import Any, Dict

import aiohttp

USER_AGENT = "dependency-graph/0.2"
DEFAULT_TIMEOUT = 15
METADATA_SUFFIX = "/json"
HTTP_NOT_FOUND = 404
HTTP_CLIENT_ERROR = 400


class RepositoryError(Exception):
    """Ошибка получения метаданных из репозитория."""


def build_url(base_url: str, package: str) -> str:
    """Собирает адрес метаданных пакета из адреса репозитория."""
    return f"{base_url.rstrip('/')}/{package}{METADATA_SUFFIX}"


async def fetch_metadata(session: aiohttp.ClientSession,
                         base_url: str, package: str,
                         timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Загружает и разбирает метаданные пакета из репозитория."""
    url = build_url(base_url, package)
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with session.get(url, timeout=client_timeout) as response:
            _check_status(response.status, package)
            raw = await response.read()
    except aiohttp.ClientError as error:
        raise RepositoryError(f"репозиторий недоступен: {error}")
    except asyncio.TimeoutError:
        raise RepositoryError(
            f"репозиторий не ответил за {timeout} секунд")
    return _decode(raw, package)


def _check_status(status: int, package: str) -> None:
    """Проверяет код ответа и бросает понятную ошибку."""
    if status == HTTP_NOT_FOUND:
        raise RepositoryError(
            f"пакет {package!r} не найден в репозитории (HTTP 404)")
    if status >= HTTP_CLIENT_ERROR:
        raise RepositoryError(f"репозиторий ответил ошибкой HTTP {status}")


def _decode(raw: bytes, package: str) -> Dict[str, Any]:
    """Разбирает тело ответа как JSON-объект метаданных."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RepositoryError(
            f"ответ репозитория для {package!r} — не JSON")
    if not isinstance(data, dict) or "info" not in data:
        raise RepositoryError(
            f"в ответе репозитория для {package!r} нет блока info")
    return data
