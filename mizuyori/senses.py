"""Чувства агентов: уши (слушают папку «Приёмная»), ноги (ходят по сети и ищут)."""
from __future__ import annotations

import html
import logging
import re
import threading
import time
import urllib.parse
import urllib.request

from . import agents, archive, paths

журнал = logging.getLogger("mizuyori.чувства")

ПРИЁМНАЯ = paths.ПАПКА_ДАННЫХ / "Приёмная"
ГОТОВО = ПРИЁМНАЯ / "обработано"
ОПРОС_СЕК = 20
_поток = None
_замок = threading.Lock()


# ---- Уши: слушают «Приёмную» ---------------------------------------------------------------

def прослушать(база, настройки_ии: dict | None = None) -> list[str]:
    """Новые файлы из «Приёмной» → Архивариус раскладывает по контрагентам и договорам."""
    ПРИЁМНАЯ.mkdir(parents=True, exist_ok=True)
    итог = []
    for п in sorted(ПРИЁМНАЯ.iterdir()):
        if not п.is_file() or п.name.startswith(("~", ".")):
            continue
        if time.time() - п.stat().st_mtime < 3:           # файл ещё копируется
            continue
        try:
            with agents.работа("архивариус", "услышал новый файл", п.name) as з:
                ф = archive.принять_файл(база, настройки_ии, п.name, п.read_bytes())
                где = ф.get("путь") or ф.get("имя") or п.name
                з["результат"] = f"разложил: {где}"
                з["польза"] = 2
            ГОТОВО.mkdir(exist_ok=True)
            цель = ГОТОВО / п.name
            if цель.exists():
                цель = ГОТОВО / f"{int(time.time())}_{п.name}"
            п.replace(цель)
            agents.написать("архивариус", "смотрящий", f"Принял файл «{п.name}» из приёмной")
            итог.append(f"{п.name} → {где}")
        except Exception:
            журнал.exception("Файл из приёмной не принят: %s", п.name)
    return итог


def запустить_уши(база, получить_настройки_ии) -> None:
    global _поток
    with _замок:
        if _поток and _поток.is_alive():
            return

        def цикл():
            time.sleep(15)
            while True:
                try:
                    прослушать(база, получить_настройки_ии())
                except Exception:
                    журнал.exception("Уши агентов")
                time.sleep(ОПРОС_СЕК)

        _поток = threading.Thread(target=цикл, name="mizuyori-ears", daemon=True)
        _поток.start()


# ---- Ноги: поиск в сети -----------------------------------------------------------------------

СЛОВА_ПОИСКА = re.compile(r"^\s*(?:[а-яё\-]+[,:]\s*)?(?:найди|поищи|загугли|посмотри в (?:интернете|сети)|узнай в (?:интернете|сети))\s+(.{3,200})", re.I)


def просят_поиск(текст: str) -> str:
    м = СЛОВА_ПОИСКА.match(текст.strip())
    return м.group(1).strip(" .?!") if м else ""


def _чистка(т: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", т)).split())


def искать(запрос: str, сколько: int = 5, получить=None) -> list[dict]:
    """Поисковая выдача DuckDuckGo (без ключей). Ошибки сети поднимаются наружу."""
    адрес = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": запрос})
    if получить:
        страница = получить(адрес)
    else:
        з = urllib.request.Request(адрес, headers={"User-Agent": "Mozilla/5.0 (Mizuyori)"})
        страница = urllib.request.urlopen(з, timeout=12).read().decode("utf-8", "replace")
    итог = []
    for блок in re.findall(r'<div class="result[^"]*results_links.*?(?=<div class="result[^"]*results_links|$)', страница, re.S):
        с = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', блок, re.S)
        if not с:
            continue
        ссылка = html.unescape(с.group(1))
        if "uddg=" in ссылка:
            ссылка = urllib.parse.unquote(ссылка.split("uddg=", 1)[1].split("&", 1)[0])
        о = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', блок, re.S)
        итог.append({"название": _чистка(с.group(2))[:140], "ссылка": ссылка, "кратко": _чистка(о.group(1))[:240] if о else ""})
        if len(итог) >= сколько:
            break
    return итог


def найти_для_чата(запрос: str, агент: str = "снабженец", получить=None) -> tuple[str, str]:
    """(факты для ИИ, готовое сообщение). Без сети — честное «не дошёл»."""
    with agents.работа(агент, "сходил в интернет", запрос[:80]) as з:
        try:
            результаты = искать(запрос, получить=получить)
        except Exception as ошибка:
            журнал.warning("Поиск не удался: %s", ошибка)
            з["результат"] = "сеть недоступна"
            return ("Хозяин просил найти в интернете, но выйти в сеть не вышло. Скажи об этом одной фразой.",
                    "🦶 Не смог выйти в интернет (нет сети или поиск закрыт). Проверьте подключение.")
        з["результат"] = f"нашёл {len(результаты)}"
        з["польза"] = 2 if результаты else 0
    if not результаты:
        return ("Поиск в интернете ничего не дал. Скажи об этом одной фразой.", f"🦶 По запросу «{запрос}» ничего не нашёл.")
    строки = [f"- [{р['название']}]({р['ссылка']})" + (f" — {р['кратко']}" if р["кратко"] else "") for р in результаты]
    return (f"Агент сходил в интернет по запросу «{запрос}» и принёс ссылки. Скажи одной фразой.",
            f"🦶 Нашёл по запросу «{запрос}»:\n" + "\n".join(строки) + "\n\nЦены и условия проверьте на самих страницах.")
