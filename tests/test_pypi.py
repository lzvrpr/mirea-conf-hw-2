"""Тесты загрузки метаданных пакета из репозитория."""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import aiohttp

from src.pypi import (PyPiProvider, RepositoryError, build_url,
                      fetch_metadata)

DATA_DIR = Path(__file__).parent / "data"
BASE_URL = "https://pypi.org/pypi"


class FakeResponse:
    """Подменяет HTTP-ответ aiohttp."""

    def __init__(self, status: int, payload: bytes) -> None:
        """Запоминает код и тело ответа."""
        self.status = status
        self.payload = payload

    async def read(self) -> bytes:
        """Возвращает тело ответа."""
        return self.payload

    async def __aenter__(self) -> "FakeResponse":
        """Позволяет использовать ответ в выражении async with."""
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Закрывает подменный ответ: делать нечего."""
        return None


class FakeSession:
    """Подменяет aiohttp.ClientSession."""

    def __init__(self, response: FakeResponse) -> None:
        """Запоминает ответ, который будет отдан на любой запрос."""
        self.response = response

    def get(self, url: str, timeout: Any = None) -> FakeResponse:
        """Отдаёт подменный ответ на любой GET."""
        return self.response


class BrokenSession:
    """Подменяет сессию, у которой запрос всегда падает."""

    def __init__(self, error: BaseException) -> None:
        """Запоминает исключение, которое бросит запрос."""
        self.error = error

    def get(self, url: str, timeout: Any = None) -> FakeResponse:
        """Бросает заданное исключение вместо запроса."""
        raise self.error


class BuildUrlTest(unittest.TestCase):
    """Проверяет сборку адреса метаданных."""

    def test_base_url(self) -> None:
        """Адрес собирается из базы и имени пакета."""
        self.assertEqual(build_url(BASE_URL, "requests"),
                         "https://pypi.org/pypi/requests/json")

    def test_trailing_slash(self) -> None:
        """Завершающий слэш в базе не даёт двойного слэша."""
        self.assertEqual(build_url(BASE_URL + "/", "requests"),
                         "https://pypi.org/pypi/requests/json")


class FetchTest(unittest.IsolatedAsyncioTestCase):
    """Проверяет разбор ответов репозитория."""

    def _prepare(self) -> None:
        """Загружает образец ответа из файла."""
        self.payload = (DATA_DIR / "requests.json").read_bytes()

    async def test_success(self) -> None:
        """Метаданные разбираются из ответа репозитория."""
        self._prepare()
        session = FakeSession(FakeResponse(200, self.payload))
        metadata = await fetch_metadata(session, BASE_URL, "requests")
        self.assertEqual(metadata["info"]["version"], "2.34.2")
        self.assertEqual(len(metadata["info"]["requires_dist"]), 6)

    async def test_not_found(self) -> None:
        """Ответ 404 превращается в понятную ошибку."""
        self._prepare()
        session = FakeSession(FakeResponse(404, b""))
        with self.assertRaises(RepositoryError) as caught:
            await fetch_metadata(session, BASE_URL, "no-such-package")
        self.assertIn("не найден", str(caught.exception))

    async def test_server_error(self) -> None:
        """Прочие ошибки HTTP называют код ответа."""
        self._prepare()
        session = FakeSession(FakeResponse(500, b""))
        with self.assertRaises(RepositoryError) as caught:
            await fetch_metadata(session, BASE_URL, "requests")
        self.assertIn("500", str(caught.exception))

    async def test_network_error(self) -> None:
        """Ошибка сети превращается в понятную ошибку."""
        self._prepare()
        session = BrokenSession(aiohttp.ClientError("нет сети"))
        with self.assertRaises(RepositoryError) as caught:
            await fetch_metadata(session, BASE_URL, "requests")
        self.assertIn("недоступен", str(caught.exception))

    async def test_timeout(self) -> None:
        """Молчание репозитория превращается в понятную ошибку."""
        self._prepare()
        session = BrokenSession(asyncio.TimeoutError())
        with self.assertRaises(RepositoryError) as caught:
            await fetch_metadata(session, BASE_URL, "requests")
        self.assertIn("не ответил", str(caught.exception))

    async def test_broken_json(self) -> None:
        """Не-JSON ответ отвергается."""
        self._prepare()
        session = FakeSession(FakeResponse(200, b"<html>"))
        with self.assertRaises(RepositoryError):
            await fetch_metadata(session, BASE_URL, "requests")

    async def test_no_info_block(self) -> None:
        """JSON без блока info отвергается."""
        self._prepare()
        payload = json.dumps({"releases": {}}).encode("utf-8")
        session = FakeSession(FakeResponse(200, payload))
        with self.assertRaises(RepositoryError):
            await fetch_metadata(session, BASE_URL, "requests")


class ProviderTest(unittest.IsolatedAsyncioTestCase):
    """Проверяет источник зависимостей из репозитория."""

    async def test_filters_extras(self) -> None:
        """Зависимости из extras в граф не попадают."""
        metadata = {"info": {"requires_dist": [
            "a>=1.0",
            'b; extra == "dev"',
        ]}}
        session = FakeSession(FakeResponse(200, b""))
        provider = PyPiProvider(session, BASE_URL)
        with mock.patch("src.pypi.fetch_metadata",
                        new=mock.AsyncMock(return_value=metadata)):
            self.assertEqual(await provider("x"), ["a"])

    async def test_parallel_requests_are_shared(self) -> None:
        """Два одновременных запроса одного пакета дают один HTTP-запрос."""
        calls = []

        async def fake(session: Any, base_url: str, name: str,
                       timeout: float = 15) -> dict:
            """Считает вызовы и отдаёт фиксированные метаданные."""
            calls.append(name)
            await asyncio.sleep(0.01)
            return {"info": {"requires_dist": ["a"]}}

        session = FakeSession(FakeResponse(200, b""))
        provider = PyPiProvider(session, BASE_URL)
        with mock.patch("src.pypi.fetch_metadata", new=fake):
            results = await asyncio.gather(provider("x"), provider("x"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results, [["a"], ["a"]])

    async def test_cache(self) -> None:
        """Повторный запрос берётся из кэша."""
        metadata = {"info": {"requires_dist": ["a"]}}
        session = FakeSession(FakeResponse(200, b""))
        provider = PyPiProvider(session, BASE_URL)
        with mock.patch("src.pypi.fetch_metadata",
                        new=mock.AsyncMock(return_value=metadata)) as fetch:
            await provider("x")
            await provider("x")
        self.assertEqual(fetch.await_count, 1)
