"""Клиент MCP (Model Context Protocol): стандартные серверы как инструменты агентов без правки кода.

Берём минимум протокола: запуск сервера дочерним процессом (stdio, JSON-RPC по строкам), initialize, tools/list, tools/call.
Включённый сервер регистрирует свои инструменты в реестре `tools` под именем «сервер.инструмент» (набор «внешние»);
выключенный — убирает и останавливает процесс. Дальше они подчиняются тому же файрволу: наборы, «только чтение», подтверждение.

Каталог закрытый: Fetch и Time из modelcontextprotocol/servers. Произвольную команду через интерфейс запустить нельзя —
запуск процессов по запросу из браузера был бы дырой. Нужен `uvx` (пакет uv); в Windows для npx-серверов понадобилась бы обёртка `cmd /c`.
"""

from __future__ import annotations

import atexit
import json
import logging
import queue
import re
import shutil
import subprocess
import threading
from concurrent.futures import Future
from typing import Callable

from . import tools

журнал = logging.getLogger("mizuyori.mcp")

ВЕРСИЯ_ПРОТОКОЛА = "2024-11-05"
ТАЙМАУТ_ЗАПУСКА = 60.0
ТАЙМАУТ_ВЫЗОВА = 60.0

КАТАЛОГ: dict[str, dict] = {
    "fetch": {"имя": "Fetch", "что": "загружает веб-страницу и превращает её в удобный для модели текст",
              "команда": ["uvx", "mcp-server-fetch"], "только_чтение": True},
    "time": {"имя": "Time", "что": "текущее время и перевод времени между часовыми поясами",
             "команда": ["uvx", "mcp-server-time"], "только_чтение": True},
}


class ОшибкаMCP(RuntimeError):
    pass


class Сервер:
    """Один запущенный MCP-сервер."""

    def __init__(self, ключ: str, команда: list[str]):
        self.ключ, self.команда = ключ, команда
        self._процесс: subprocess.Popen | None = None
        self._ждущие: dict[int, Future] = {}
        self._номер = 0
        self._замок = threading.Lock()
        self.инструменты: list[dict] = []

    # ---- процесс и обмен -----------------------------------------------------------------------
    def запустить(self) -> None:
        исполняемый = shutil.which(self.команда[0])
        if not исполняемый:
            raise ОшибкаMCP(f"не найдена программа «{self.команда[0]}» (для Fetch и Time нужен uv: https://docs.astral.sh/uv/)")
        self._процесс = subprocess.Popen([исполняемый, *self.команда[1:]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._читать, daemon=True, name=f"mcp-{self.ключ}").start()
        self._запрос("initialize", {"protocolVersion": ВЕРСИЯ_ПРОТОКОЛА, "capabilities": {},
                                    "clientInfo": {"name": "Mizuyori", "version": "1"}}, ТАЙМАУТ_ЗАПУСКА)
        self._отправить({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.инструменты = self._запрос("tools/list", {}, ТАЙМАУТ_ЗАПУСКА).get("tools", [])

    def _отправить(self, сообщение: dict) -> None:
        if not self._процесс or self._процесс.poll() is not None:
            raise ОшибкаMCP("сервер не запущен")
        with self._замок:
            self._процесс.stdin.write(json.dumps(сообщение, ensure_ascii=False) + "\n")
            self._процесс.stdin.flush()

    def _запрос(self, метод: str, параметры: dict, таймаут: float) -> dict:
        with self._замок:
            self._номер += 1
            номер = self._номер
            будущее: Future = Future()
            self._ждущие[номер] = будущее
        self._отправить({"jsonrpc": "2.0", "id": номер, "method": метод, "params": параметры})
        try:
            ответ = будущее.result(timeout=таймаут)
        except Exception as е:
            raise ОшибкаMCP(f"сервер не ответил на «{метод}»: {е or 'таймаут'}") from None
        finally:
            self._ждущие.pop(номер, None)
        if "error" in ответ:
            raise ОшибкаMCP(str(ответ["error"].get("message", ответ["error"]))[:300])
        return ответ.get("result") or {}

    def _читать(self) -> None:
        for строка in self._процесс.stdout:
            try:
                с = json.loads(строка)
            except ValueError:
                continue                               # лишний вывод сервера — не протокол
            б = self._ждущие.get(с.get("id")) if isinstance(с, dict) else None
            if б and not б.done():
                б.set_result(с)
        for б in list(self._ждущие.values()):          # процесс закончился — всем ждущим ошибка
            if not б.done():
                б.set_exception(ОшибкаMCP("сервер завершился"))

    def вызвать(self, инструмент: str, аргументы: dict) -> str:
        р = self._запрос("tools/call", {"name": инструмент, "arguments": аргументы}, ТАЙМАУТ_ВЫЗОВА)
        текст = "\n".join(ч.get("text", "") for ч in р.get("content", []) if isinstance(ч, dict) and ч.get("type") == "text")
        if р.get("isError"):
            raise ОшибкаMCP(текст[:300] or "инструмент вернул ошибку")
        return текст

    def остановить(self) -> None:
        п = self._процесс
        if п and п.poll() is None:
            try:
                п.stdin.close()
                п.terminate()
                п.wait(timeout=5)
            except Exception:
                п.kill()
        if п and п.stdout:
            try:
                п.stdout.close()
            except Exception:
                pass
        self._процесс = None

    @property
    def работает(self) -> bool:
        return bool(self._процесс and self._процесс.poll() is None)


# ---- Подключение к реестру инструментов ----------------------------------------------------------

_серверы: dict[str, Сервер] = {}
_ошибки: dict[str, str] = {}
_зарегистрированы: dict[str, list[str]] = {}
_читать_состояние: Callable[[], dict] | None = None
_писать_состояние: Callable[[dict], None] | None = None


def подключить(читать: Callable[[], dict], писать: Callable[[dict], None]) -> None:
    global _читать_состояние, _писать_состояние
    _читать_состояние, _писать_состояние = читать, писать


def включённые() -> list[str]:
    с = (_читать_состояние() if _читать_состояние else {}) or {}
    return [к for к in с.get("включены", []) if к in КАТАЛОГ]


_АРГУМЕНТ_ПО_ИМЕНИ = (
    ("url", lambda т: __import__("mizuyori.page_snapshot", fromlist=["x"]).найти_адрес(т)),
    ("timezone", lambda т: next(iter(re.findall(r"[A-Za-z]+(?:/[A-Za-z_\-]+)+|UTC", т)), "")),
)


def собрать_аргументы(схема: dict, описание: str) -> dict:
    """Описание шага → аргументы инструмента: JSON-объект из текста берётся как есть, иначе обязательные строки заполняются по имени."""
    м = re.search(r"\{.*\}", описание, re.S)
    if м:
        try:
            готовые = json.loads(м.group(0))
            if isinstance(готовые, dict):
                return готовые
        except ValueError:
            pass
    свойства = (схема or {}).get("properties", {})
    аргументы = {}
    for имя in (схема or {}).get("required", list(свойства)[:1]):
        значение = ""
        for кусок, достать in _АРГУМЕНТ_ПО_ИМЕНИ:
            if кусок in имя.casefold():
                значение = достать(описание)
        аргументы[имя] = значение or описание
    return аргументы


def _проверить_адреса(аргументы: dict) -> None:
    from . import page_snapshot
    for к, з in аргументы.items():
        if isinstance(з, str) and к.casefold() in ("url", "uri", "href"):
            ок, причина = page_snapshot.адрес_допустим(з)
            if not ок:
                raise PermissionError(f"Вызов заблокирован: {причина}")


def _зарегистрировать(ключ: str, сервер: Сервер) -> None:
    имена = []
    сведения = КАТАЛОГ[ключ]
    for т in сервер.инструменты:
        имя = f"{ключ}.{т['name']}"
        только_чтение = сведения.get("только_чтение") or bool((т.get("annotations") or {}).get("readOnlyHint"))
        схема = т.get("inputSchema") or {}

        def вызов(задание: dict, _т=т["name"], _схема=схема, _ключ=ключ) -> str:
            с = _серверы.get(_ключ)
            if not с or not с.работает:
                raise ОшибкаMCP("сервер выключен или остановился")
            аргументы = собрать_аргументы(_схема, задание.get("описание", ""))
            _проверить_адреса(аргументы)
            return с.вызвать(_т, аргументы)
        tools.ИНСТРУМЕНТЫ[имя] = tools.Инструмент(имя, (т.get("description") or сведения["что"])[:200].split("\n")[0],
                                                  not только_чтение, вызов, None, "внешние")
        имена.append(имя)
    _зарегистрированы[ключ] = имена


def запустить_сервер(ключ: str) -> None:
    остановить_сервер(ключ)
    сервер = Сервер(ключ, КАТАЛОГ[ключ]["команда"])
    try:
        сервер.запустить()
    except Exception as е:
        сервер.остановить()
        _ошибки[ключ] = str(е)[:200]
        raise
    _ошибки.pop(ключ, None)
    _серверы[ключ] = сервер
    _зарегистрировать(ключ, сервер)


def остановить_сервер(ключ: str) -> None:
    for имя in _зарегистрированы.pop(ключ, []):
        tools.ИНСТРУМЕНТЫ.pop(имя, None)
    с = _серверы.pop(ключ, None)
    if с:
        с.остановить()


def включить(ключ: str, да: bool) -> dict:
    if ключ not in КАТАЛОГ:
        raise KeyError(ключ)
    есть = set(включённые())
    if да:
        запустить_сервер(ключ)          # не вышло — исключение, состояние не сохраняем
        есть.add(ключ)
    else:
        остановить_сервер(ключ)
        есть.discard(ключ)
        _ошибки.pop(ключ, None)
    if _писать_состояние:
        _писать_состояние({"включены": sorted(есть)})
    return состояние(ключ)


def состояние(ключ: str) -> dict:
    с = _серверы.get(ключ)
    return {"ключ": ключ, "имя": КАТАЛОГ[ключ]["имя"], "что": КАТАЛОГ[ключ]["что"],
            "команда": " ".join(КАТАЛОГ[ключ]["команда"]), "включён": ключ in включённые(),
            "работает": bool(с and с.работает), "ошибка": _ошибки.get(ключ, ""),
            "инструменты": list(_зарегистрированы.get(ключ, []))}


def каталог() -> list[dict]:
    return [состояние(к) for к in КАТАЛОГ]


def запустить_включённые() -> None:
    """При старте Mizuyori: поднять сохранённые серверы в фоне, чтобы запуск не ждал сеть и uvx."""
    def цикл():
        for к in включённые():
            try:
                запустить_сервер(к)
            except Exception as е:
                журнал.warning("MCP-сервер «%s» не запустился: %s", к, е)
    threading.Thread(target=цикл, daemon=True, name="mcp-старт").start()


def остановить_все() -> None:
    for к in list(_серверы):
        остановить_сервер(к)


atexit.register(остановить_все)
