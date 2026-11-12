"""Страницы поиска через настоящий Chrome: у браузера с профилем капча почти не появляется.

Режимы (настройка агенты → браузер_для_поиска):
- "chrome" — Mizuyori сам запускает Chrome с отдельным профилем в data/браузер и держит его в фоне;
- "http://127.0.0.1:9222" — подключается к уже запущенному Chrome (запуск: chrome --remote-debugging-port=9222 --user-data-dir=<своя папка>).
  Chrome 136+ не открывает отладочный порт на профиле по умолчанию, поэтому нужна отдельная папка.

Нужен пакет playwright (pip install playwright); браузер скачивать не нужно, берётся установленный Chrome.
Sync-API playwright живёт в одном потоке, поэтому весь браузер работает в отдельном потоке-«рабочем»,
а остальные потоки отправляют ему адреса через очередь.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from concurrent.futures import Future

from .paths import ПАПКА_ДАННЫХ

журнал = logging.getLogger("mizuyori.браузер")

ТАЙМАУТ_СТРАНИЦЫ_МС = 20000
ПАУЗА_ПОСЛЕ_СБОЯ = 600.0

_очередь: "queue.Queue[tuple[str, Future]]" = queue.Queue()
_поток: threading.Thread | None = None
_режим = ""
_сбой_до = 0.0
_замок = threading.Lock()


def настроить(режим: str) -> None:
    global _режим
    _режим = (режим or "").strip()


def включён() -> bool:
    return bool(_режим) and time.monotonic() >= _сбой_до


def _рабочий(режим: str) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as п:
        if режим == "chrome":
            папка = ПАПКА_ДАННЫХ / "браузер"
            папка.mkdir(parents=True, exist_ok=True)
            контекст = п.chromium.launch_persistent_context(str(папка), channel="chrome", headless=True,
                                                            locale="ru-RU", viewport={"width": 1280, "height": 900})
            закрыть = контекст.close
        else:
            подключение = п.chromium.connect_over_cdp(режим)
            контекст = подключение.contexts[0] if подключение.contexts else подключение.new_context(locale="ru-RU")
            закрыть = lambda: None      # чужой Chrome не закрываем
        try:
            while True:
                адрес, будущее = _очередь.get()
                if адрес == "":
                    break
                страница = None
                try:
                    страница = контекст.new_page()
                    страница.goto(адрес, wait_until="domcontentloaded", timeout=ТАЙМАУТ_СТРАНИЦЫ_МС)
                    будущее.set_result(страница.content())
                except Exception as ошибка:
                    будущее.set_exception(ошибка)
                finally:
                    if страница:
                        try:
                            страница.close()
                        except Exception:
                            pass
        finally:
            закрыть()


def _запустить() -> None:
    global _поток
    with _замок:
        if _поток and _поток.is_alive():
            return
        режим = _режим

        def цель():
            try:
                _рабочий(режим)
            except Exception as ошибка:
                журнал.warning("Браузер для поиска не запустился: %s", ошибка)
                while True:                              # всем, кто ждёт, — понятная ошибка, а не зависание
                    try:
                        _, б = _очередь.get_nowait()
                    except queue.Empty:
                        break
                    if not б.done():
                        б.set_exception(RuntimeError(f"браузер недоступен: {ошибка}"))
        _поток = threading.Thread(target=цель, daemon=True, name="браузер-поиска")
        _поток.start()


def скачать(адрес: str, ожидание: float = 40.0) -> str:
    """HTML страницы из настоящего Chrome. Ошибка — исключение (вызывающий откатится на обычное скачивание)."""
    _запустить()
    б: Future = Future()
    _очередь.put((адрес, б))
    return б.result(timeout=ожидание)


def с_откатом(адрес: str, обычное) -> str:
    """Браузер, а при сбое — обычное скачивание; после сбоя браузер на 10 минут откладывается."""
    global _сбой_до
    if not включён():
        return обычное(адрес)
    try:
        return скачать(адрес)
    except Exception as ошибка:
        журнал.warning("Поиск через браузер не вышел (%s), пользуюсь обычным способом.", ошибка)
        _сбой_до = time.monotonic() + ПАУЗА_ПОСЛЕ_СБОЯ
        return обычное(адрес)
