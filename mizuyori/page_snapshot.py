"""Чтение страницы как структуры, а не картинки (идея Playwright MCP).

`снимок(адрес)` — компактный текст: заголовки, списки, ссылки, кнопки, цены. С включённым браузером для поиска это
дерево доступности настоящего Chrome (видит и то, что дорисовал JavaScript, и не ловит капчу). Без браузера — текст из
обычного скачивания HTML. `выдержка(текст, слова)` — дешёвый «поиск по снимку»: вместо всей страницы только строки со словами.
Адреса проверяются: localhost, домашняя сеть и служебные адреса закрыты (это удобство, а не граница безопасности).
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.parse
from html.parser import HTMLParser

from . import browser_fetch

ЛИМИТ_СНИМКА = 60000
ЛИМИТ_ВЫДЕРЖКИ = 3500
_АДРЕС = re.compile(r"https?://[^\s<>\"')]+", re.I)


def найти_адрес(текст: str) -> str:
    м = _АДРЕС.search(текст or "")
    return м.group(0).rstrip(".,;:") if м else ""


def адрес_допустим(адрес: str) -> tuple[bool, str]:
    р = urllib.parse.urlparse(адрес or "")
    if р.scheme not in ("http", "https") or not р.hostname:
        return False, "нужен адрес http:// или https://"
    имя = р.hostname.casefold()
    if имя in ("localhost",) or имя.endswith((".local", ".internal", ".localdomain")):
        return False, "локальные адреса закрыты"
    try:
        адреса = {ipaddress.ip_address(имя)}
    except ValueError:
        try:
            адреса = {ipaddress.ip_address(а[4][0]) for а in socket.getaddrinfo(имя, None)}
        except OSError:
            return True, ""          # не нашли имя — пусть ошибку даст само скачивание
    for а in адреса:
        if а.is_private or а.is_loopback or а.is_link_local or а.is_reserved or а.is_multicast:
            return False, "адрес из внутренней сети закрыт"
    return True, ""


class _Читатель(HTMLParser):
    _БЛОКИ = {"p", "div", "section", "article", "li", "tr", "br", "ul", "ol", "table", "header", "footer", "h1", "h2", "h3", "h4", "main"}
    _ПРОПУСК = {"script", "style", "noscript", "svg", "head", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.строки: list[str] = []
        self._тек: list[str] = []
        self._пропуск = 0
        self._заголовок = ""
        self._ссылка = ""

    def _сброс(self):
        текст = " ".join("".join(self._тек).split())
        if текст:
            self.строки.append((self._заголовок + текст) if self._заголовок else текст)
        self._тек, self._заголовок = [], ""

    def handle_starttag(self, тег, атрибуты):
        if тег in self._ПРОПУСК:
            self._пропуск += 1
            return
        if тег in self._БЛОКИ:
            self._сброс()
        if тег in ("h1", "h2", "h3", "h4"):
            self._заголовок = "#" * int(тег[1]) + " "
        elif тег == "li":
            self._заголовок = "- "
        elif тег == "a":
            self._ссылка = dict(атрибуты).get("href") or ""
        elif тег == "button":
            self._тек.append("[кнопка] ")
        elif тег == "input":
            а = dict(атрибуты)
            if а.get("type") not in ("hidden", "submit", "button") and (а.get("placeholder") or а.get("name")):
                self._тек.append(f"[поле: {а.get('placeholder') or а.get('name')}] ")

    def handle_endtag(self, тег):
        if тег in self._ПРОПУСК:
            self._пропуск = max(0, self._пропуск - 1)
            return
        if тег == "a" and self._ссылка.startswith("http"):
            self._тек.append(f" ({self._ссылка[:90]})")
            self._ссылка = ""
        if тег in self._БЛОКИ:
            self._сброс()

    def handle_data(self, данные):
        if not self._пропуск:
            self._тек.append(данные)


def html_в_текст(текст_html: str) -> str:
    """HTML → строки: «# заголовок», «- пункт», ссылки с адресом, «[кнопка]», «[поле: …]». Повторы подряд убираются."""
    р = _Читатель()
    р.feed(html.unescape(текст_html) if "&lt;" in текст_html[:2000] else текст_html)
    р._сброс()
    итог, прошлая = [], ""
    for строка in р.строки:
        if строка != прошлая:
            итог.append(строка)
        прошлая = строка
    return "\n".join(итог)[:ЛИМИТ_СНИМКА]


def снимок(адрес: str) -> str:
    ок, причина = адрес_допустим(адрес)
    if not ок:
        raise ValueError(причина)
    if browser_fetch.включён():
        try:
            return browser_fetch.снимок(адрес)[:ЛИМИТ_СНИМКА]
        except Exception:
            pass                       # браузер не вышел — обычное скачивание ниже
    from . import senses
    return html_в_текст(senses._скачать(адрес))


def выдержка(текст: str, слова: list[str] | None = None, лимит: int = ЛИМИТ_ВЫДЕРЖКИ) -> str:
    """Без слов — начало страницы. Со словами — только строки, где они встречаются, с соседней строкой для контекста."""
    слова = [с.casefold() for с in (слова or []) if len(с) > 1]
    строки = текст.splitlines()
    if not слова:
        return текст[:лимит]
    попадания = sorted({j for и, с in enumerate(строки) if any(сл in с.casefold() for сл in слова)
                        for j in (и - 1, и, и + 1) if 0 <= j < len(строки)})
    if not попадания:
        return "Ничего подходящего на странице не найдено."
    итог, прошлый = [], -2
    for и in попадания:
        if и != прошлый + 1:
            итог.append("…")
        итог.append(строки[и])
        прошлый = и
    return "\n".join(итог)[:лимит]
