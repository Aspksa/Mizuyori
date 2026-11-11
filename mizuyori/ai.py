"""ИИ для чата через cloud.ru (Evolution Foundation Models).

API у cloud.ru совместим с OpenAI:
  адрес      https://foundation-models.api.cloud.ru/v1
  ключ       заголовок «Authorization: Bearer <API-ключ>»
  модели     GET  /models
  ответ      POST /chat/completions  (можно потоком: "stream": true)

Ключ создаётся в личном кабинете cloud.ru: Пользователи → Сервисные аккаунты →
аккаунт → «Создать API-ключ», сервис — Foundation Models.

Работает только на стандартной библиотеке Python, без лишних зависимостей.
"""

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime

журнал = logging.getLogger("mizuyori.ии")

АДРЕС_CLOUD_RU = "https://foundation-models.api.cloud.ru/v1"
ЗАГЛУШКА = ("ИИ пока не подключён. Откройте настройки проекта (шестерёнка слева вверху) → "
            "вкладка «ИИ», вставьте ключ cloud.ru и выберите модель.")

# Модели, которые не умеют отвечать в чате (эмбеддинги, переранжирование, речь)
_НЕ_ДЛЯ_ЧАТА = re.compile(r"embed|rerank|whisper|bge-|e5-|tts|asr|speech", re.I)


class ОшибкаИИ(Exception):
    """Ошибка с понятным текстом для человека."""


# ---- Связь с сервером ------------------------------------------------------

def _контекст_ssl() -> ssl.SSLContext:
    # Сертификаты берутся из системы (в Windows — из хранилища Windows)
    return ssl.create_default_context()


def _понятная_ошибка(код: int, тело: str) -> str:
    подробно = ""
    try:
        данные = json.loads(тело)
        ошибка = данные.get("error", данные)
        подробно = ошибка.get("message") if isinstance(ошибка, dict) else str(ошибка)
    except (ValueError, AttributeError):
        подробно = тело[:200]
    подробно = f" ({подробно})" if подробно else ""
    if код == 401:
        return f"Ключ не подошёл: cloud.ru ответил «401 — нет доступа». Проверьте ключ и срок его действия{подробно}."
    if код == 403:
        return f"Нет прав: у ключа нет доступа к Foundation Models{подробно}."
    if код == 404:
        return f"Не найдено: проверьте адрес API и название модели{подробно}."
    if код == 429:
        return f"Слишком много запросов или закончились токены. Подождите немного{подробно}."
    if код >= 500:
        return f"Сервер cloud.ru сейчас не отвечает (ошибка {код}). Попробуйте позже{подробно}."
    return f"Ошибка {код}{подробно}."


def _открыть(адрес: str, ключ: str, путь: str, тело: dict | None = None, таймаут: float = 30):
    if not ключ:
        raise ОшибкаИИ("Не указан ключ cloud.ru.")
    запрос = urllib.request.Request(
        адрес.rstrip("/") + путь,
        data=json.dumps(тело).encode("utf-8") if тело is not None else None,
        method="POST" if тело is not None else "GET",
        headers={
            "Authorization": f"Bearer {ключ.strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "Mizuyori",
        },
    )
    try:
        return urllib.request.urlopen(запрос, timeout=таймаут, context=_контекст_ssl())
    except urllib.error.HTTPError as ошибка:
        тело_ответа = ошибка.read().decode("utf-8", "replace")
        журнал.warning("cloud.ru ответил %s на %s: %s", ошибка.code, путь, тело_ответа[:300])
        raise ОшибкаИИ(_понятная_ошибка(ошибка.code, тело_ответа)) from None
    except urllib.error.URLError as ошибка:
        причина = ошибка.reason
        if isinstance(причина, ssl.SSLError):
            raise ОшибкаИИ(f"Ошибка защищённого соединения: {причина}. Проверьте дату и время на компьютере.") from None
        raise ОшибкаИИ(f"Нет связи с {адрес}: {причина}. Проверьте интернет.") from None
    except TimeoutError:
        raise ОшибкаИИ("cloud.ru слишком долго не отвечает.") from None


# ---- Модели ----------------------------------------------------------------

def список_моделей(адрес: str, ключ: str) -> list[dict]:
    """Модели, доступные по ключу. Заодно проверяет, что ключ работает."""
    with _открыть(адрес, ключ, "/models", таймаут=20) as ответ:
        данные = json.loads(ответ.read().decode("utf-8"))
    модели = данные.get("data", данные if isinstance(данные, list) else [])
    итог = []
    for м in модели:
        имя = м.get("id") if isinstance(м, dict) else str(м)
        if not имя:
            continue
        итог.append({
            "id": имя,
            "владелец": (м.get("owned_by") if isinstance(м, dict) else "") or имя.split("/")[0],
            "для_чата": not _НЕ_ДЛЯ_ЧАТА.search(имя),
        })
    итог.sort(key=lambda м: (not м["для_чата"], м["id"].lower()))
    return итог


# ---- Ответ -----------------------------------------------------------------

def подключён(настройки_ии: dict) -> bool:
    return bool(настройки_ии.get("включён") and настройки_ии.get("ключ") and настройки_ии.get("модель"))


def _сообщения(история: list[dict], настройки_ии: dict, имя: str) -> list[dict]:
    сейчас = datetime.now()
    характер = (настройки_ии.get("характер") or "").strip()
    система = (
        f"{характер}\n\n" if характер else ""
    ) + (
        f"Тебя зовут {имя}. Отвечай по-русски, если тебя не просят иначе. "
        f"Сейчас {сейчас:%d.%m.%Y %H:%M}, {['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье'][сейчас.weekday()]}."
    )
    сообщения = [{"role": "system", "content": система}]
    for с in история:
        сообщения.append({"role": "assistant" if с["роль"] == "ии" else "user", "content": с["текст"]})
    return сообщения


def _тело(история, настройки_ии, имя, поток: bool) -> dict:
    return {
        "model": настройки_ии["модель"],
        "messages": _сообщения(история, настройки_ии, имя),
        "temperature": настройки_ии.get("температура", 0.7),
        "max_tokens": int(настройки_ии.get("длина", 2000)),
        "stream": поток,
    }


_РАЗМЫШЛЕНИЯ = re.compile(r"<think>.*?</think>\s*", re.S)


def убрать_размышления(текст: str) -> str:
    """Модели-«мыслители» (DeepSeek-R1 и др.) пишут ход мыслей в <think>…</think>."""
    return _РАЗМЫШЛЕНИЯ.sub("", текст).strip()


def ответ_потоком(история: list[dict], настройки_ии: dict, имя: str):
    """Отдаёт ответ кусочками по мере генерации."""
    начало = time.monotonic()
    тело = _тело(история, настройки_ии, имя, поток=True)
    with _открыть(настройки_ии["адрес"], настройки_ии["ключ"], "/chat/completions", тело, таймаут=120) as ответ:
        тип = ответ.headers.get("Content-Type", "")
        if "text/event-stream" not in тип:
            # Сервер ответил целиком, без потока
            данные = json.loads(ответ.read().decode("utf-8"))
            yield данные["choices"][0]["message"].get("content") or ""
            return
        for строка in ответ:
            строка = строка.decode("utf-8", "replace").strip()
            if not строка.startswith("data:"):
                continue
            кусок = строка[5:].strip()
            if кусок == "[DONE]":
                break
            try:
                данные = json.loads(кусок)
            except ValueError:
                continue
            if данные.get("error"):
                ошибка = данные["error"]
                raise ОшибкаИИ(ошибка.get("message", str(ошибка)) if isinstance(ошибка, dict) else str(ошибка))
            for выбор in данные.get("choices", []):
                текст = (выбор.get("delta") or {}).get("content")
                if текст:
                    yield текст
    журнал.info("Ответ ИИ (%s) за %.1f с", настройки_ии["модель"], time.monotonic() - начало)


def проверить(настройки_ии: dict, имя: str) -> dict:
    """Короткий пробный запрос к выбранной модели."""
    начало = time.monotonic()
    тело = _тело([{"роль": "пользователь", "текст": "Ответь одним коротким предложением: ты на связи?"}],
                 {**настройки_ии, "длина": 100}, имя, поток=False)
    with _открыть(настройки_ии["адрес"], настройки_ии["ключ"], "/chat/completions", тело, таймаут=60) as ответ:
        данные = json.loads(ответ.read().decode("utf-8"))
    текст = убрать_размышления(данные["choices"][0]["message"].get("content") or "")
    return {"ответ": текст, "секунд": round(time.monotonic() - начало, 1)}
