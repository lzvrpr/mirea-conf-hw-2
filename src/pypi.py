"""Загрузка метаданных пакета из репозитория PyPI.

Менеджеры пакетов и чужие библиотеки для получения зависимостей не
используются: запрос идёт через aiohttp, ответ разбирается стандартным json.
"""

import asyncio
import json
from typing import Any, Dict, List

import aiohttp

from src.graph import DependencyError
from src.requirement import direct_dependencies

USER_AGENT = "dependency-graph/0.6"
DEFAULT_TIMEOUT = 15
METADATA_SUFFIX = "/json"
HTTP_NOT_FOUND = 404
HTTP_CLIENT_ERROR = 400


class RepositoryError(DependencyError):
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


class PyPiProvider:
    """Отдаёт прямые зависимости пакета из репозитория, с кэшем в памяти.

    Кэш живёт в памяти процесса: при обходе сотен пакетов его стоит
    перенести на диск, чтобы не повторять запросы между запусками.
    """

    def __init__(self, session: aiohttp.ClientSession, base_url: str,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        """Запоминает сессию, адрес репозитория и таймаут."""
        self._session = session
        self._base_url = base_url
        self._timeout = timeout
        self._cache: Dict[str, List[str]] = {}
        self._tasks: Dict[str, Any] = {}

    async def __call__(self, name: str) -> List[str]:
        """Возвращает имена прямых зависимостей пакета.

        Зависимости из extras не входят: они ставятся только по явному
        запросу вида `pip install name[extra]`.
        """
        cached = self._cache.get(name)
        if cached is not None:
            return list(cached)
        task = self._tasks.get(name)
        if task is None:
            task = asyncio.ensure_future(self._load(name))
            self._tasks[name] = task
        return list(await task)

    async def _load(self, name: str) -> List[str]:
        """Загружает зависимости пакета и кладёт их в кэш."""
        metadata = await fetch_metadata(self._session, self._base_url,
                                        name, self._timeout)
        children = [item.name for item in direct_dependencies(metadata)
                    if not item.extra]
        self._cache[name] = children
        return children
