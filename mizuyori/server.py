"""Веб-сервер: страница и API."""

import json
import logging
import platform
import threading
import time
from datetime import date
from html import escape

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, agents, ai, memory, soul, work
from .config import (ВИД_ПО_УМОЛЧАНИЮ, ВНЕШНИЙ_ВИД, ИИ_ПО_УМОЛЧАНИЮ, МОЗГИ_ПО_УМОЛЧАНИЮ,
                     НеверныйВнешнийВид, атрибуты_html, проверить_внешний_вид, проверить_ии,
                     проверить_мозги, сохранить_настройки)
from .database import ТИПЫ_СУЩНОСТЕЙ, База, ключ_имени
from .paths import ПАПКА_СТАТИКИ, ФАЙЛ_НАСТРОЕК

журнал = logging.getLogger("mizuyori.сервер")


class ИзменениеНастроек(BaseModel):
    внешний_вид: dict


class Текст(BaseModel):
    текст: str = Field(max_length=20000)


class НоваяЗадача(BaseModel):
    текст: str = Field(max_length=2000)
    срок: str | None = None          # «ГГГГ-ММ-ДД» или нет
    список_id: int | None = None
    цель_id: int | None = None


class ИзменениеЗадачи(BaseModel):
    текст: str | None = Field(default=None, max_length=2000)
    готово: bool | None = None
    срок: str | None = None
    список_id: int | None = None
    цель_id: int | None = None


class СписокЗадач(BaseModel):
    название: str | None = Field(default=None, max_length=60)
    цвет: str | None = None
    значок: str | None = None


# Цвета и значки для списков задач
ЦВЕТА_СПИСКОВ = {
    "красный": "#e5534b",
    "оранжевый": "#f0883e",
    "жёлтый": "#d4a72c",
    "зелёный": "#3fb950",
    "бирюзовый": "#2fb8ac",
    "синий": "#4c8ef7",
    "фиолетовый": "#a371f7",
    "розовый": "#db61a2",
    "серый": "#8b949e",
}
ЗНАЧКИ_СПИСКОВ = ["📋", "🏠", "💼", "🛒", "📚", "❤️", "⭐", "💡", "🔧", "🎮", "✈️", "🎵", "🐾", "🌿", "💰", "🎁"]


def _проверить_срок(срок: str | None) -> str | None:
    if срок is None or срок == "":
        return None
    try:
        return date.fromisoformat(срок).isoformat()
    except (TypeError, ValueError):
        raise StarletteHTTPException(400, "Неверная дата срока.")


def _непустой(текст: str | None, что: str) -> str:
    текст = (текст or "").strip()
    if not текст:
        raise StarletteHTTPException(400, f"{что} не может быть пустым.")
    return текст


def создать_приложение(настройки: dict, база: База, порт: int) -> FastAPI:
    app = FastAPI(title=настройки["имя"], version=__version__,
                  docs_url=None, redoc_url=None, openapi_url=None)

    последняя_активность = [time.monotonic()]

    @app.middleware("http")
    async def отметить_активность(request: Request, вызвать_дальше):
        # Чтение страниц и фоновые опросы не мешают Душе развиваться.
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            последняя_активность[0] = time.monotonic()
        return await вызвать_дальше(request)

    # ---- Ошибки отдаются на русском ---------------------------------------

    @app.exception_handler(RequestValidationError)
    async def неверные_данные(request: Request, ошибка: RequestValidationError):
        return JSONResponse(status_code=422, content={"ошибка": "Неверные данные в запросе."})

    СТАНДАРТНЫЕ = {
        404: "Не найдено.",
        405: "Этот метод здесь не поддерживается.",
    }

    @app.exception_handler(StarletteHTTPException)
    async def http_ошибка(request: Request, ошибка: StarletteHTTPException):
        текст = ошибка.detail
        # Стандартные английские тексты заменяем русскими
        if not isinstance(текст, str) or текст.isascii():
            текст = СТАНДАРТНЫЕ.get(ошибка.status_code, f"Ошибка {ошибка.status_code}.")
        return JSONResponse(status_code=ошибка.status_code, content={"ошибка": текст})

    @app.exception_handler(Exception)
    async def внутренняя_ошибка(request: Request, ошибка: Exception):
        журнал.exception("Ошибка при обработке %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500,
                            content={"ошибка": "Внутренняя ошибка. Подробности в logs/mizuyori.log."})

    # ---- Страница -------------------------------------------------------

    @app.get("/", include_in_schema=False)
    def главная():
        # Тема подставляется сразу в HTML, чтобы страница не мигала другим цветом
        html = (ПАПКА_СТАТИКИ / "index.html").read_text(encoding="utf-8")
        html = (html.replace("{{атрибуты}}", атрибуты_html(настройки["внешний_вид"]))
                    .replace("{{имя}}", escape(настройки["имя"])))
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=ПАПКА_СТАТИКИ), name="static")

    # ---- API ------------------------------------------------------------

    @app.get("/api/status")
    def состояние():
        return {
            "имя": настройки["имя"],
            "версия": __version__,
            "python": platform.python_version(),
            "система": f"{platform.system()} {platform.release()}",
            "порт": порт,
            "база": str(база.файл),
        }

    @app.get("/api/settings")
    def получить_настройки():
        return {
            "внешний_вид": настройки["внешний_вид"],
            "по_умолчанию": ВИД_ПО_УМОЛЧАНИЮ,
            "описание": ВНЕШНИЙ_ВИД,
        }

    @app.put("/api/settings")
    def изменить_настройки(изменение: ИзменениеНастроек):
        try:
            новый = проверить_внешний_вид(изменение.внешний_вид, строго=True)
        except НеверныйВнешнийВид as ошибка:
            raise StarletteHTTPException(400, str(ошибка))
        изменено = [ВНЕШНИЙ_ВИД[к]["название"] for к in новый if новый[к] != настройки["внешний_вид"][к]]
        if изменено:
            настройки["внешний_вид"] = новый
            сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
            журнал.info("Внешний вид сохранён (изменено: %s).", ", ".join(изменено).lower())
        return получить_настройки()

    # ---- Чат ------------------------------------------------------------

    def _ии():
        return настройки["ии"]

    def _метка_ии() -> dict:
        н = _ии()
        return {"ии_подключён": ai.подключён(н), "модель": н["модель"] if ai.подключён(н) else ""}

    @app.get("/api/chat")
    def чат():
        return {"сообщения": база.сообщения(), **_метка_ии()}

    @app.post("/api/chat")
    def написать(сообщение: Текст):
        """Ответ идёт потоком: строки JSON по одной на строку.
        {"вопрос": …} → {"кусок": "…"} × N → {"ответ": …}  (или {"ошибка": "…"})"""
        текст = _непустой(сообщение.текст, "Сообщение")
        вопрос = база.добавить_сообщение("пользователь", текст)
        н = dict(_ии())

        def строка(данные: dict) -> bytes:
            return (json.dumps(данные, ensure_ascii=False) + "\n").encode("utf-8")

        def поток():
            yield строка({"вопрос": вопрос})
            if not ai.подключён(н):
                yield строка({"ответ": база.добавить_сообщение("ии", ai.ЗАГЛУШКА)})
                return
            # старые подсказки «ИИ не подключён» в память ИИ не берём
            история = [с for с in база.сообщения(max(н["история"], 1) + 10) if с["текст"] != ai.ЗАГЛУШКА]
            история = история[-max(н["история"], 1):]
            собрано = []
            try:
                контекст = memory.контекст_для_ответа(база, н, текст)
            except Exception:
                журнал.exception("Не удалось собрать память для ответа")
                контекст = {}
            try:
                with agents.работа("чат", "ответил в чате", f"вы написали: «{' '.join(текст.split())[:60]}»") as запись:
                    for кусок in ai.ответ_потоком(история, н, настройки["имя"], контекст):
                        собрано.append(кусок)
                        yield строка({"кусок": кусок})
                    м, о = ai.отделить_мысль(ai.убрать_размышления("".join(собрано)))
                    запись["результат"] = f"ответ {len(о)} знаков" + (" · с мыслью" if м else "")
                    запись["польза"] = 1
            except ai.ОшибкаИИ as ошибка:
                журнал.warning("ИИ не ответил: %s", ошибка)
                yield строка({"ошибка": str(ошибка)})
                return
            except Exception:
                журнал.exception("ИИ не смог ответить")
                yield строка({"ошибка": "Непредвиденная ошибка ИИ. Подробности в logs/mizuyori.log."})
                return
            мысль, ответ = ai.отделить_мысль(ai.убрать_размышления("".join(собрано)))
            yield строка({"ответ": база.добавить_сообщение("ии", ответ or "…", мысль)})
            # Память и сводка — в фоне, чтобы не задерживать ответ
            threading.Thread(target=memory.после_ответа, args=(база, н, текст, ответ, вопрос["id"]),
                             daemon=True).start()

        return StreamingResponse(поток(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    # ---- Память ИИ ----------------------------------------------------------

    class Факт(BaseModel):
        факт: str | None = Field(default=None, max_length=300)
        категория: str | None = None
        важность: int | None = Field(default=None, ge=1, le=5)

    def _проверить_категорию(категория: str | None) -> str | None:
        if категория is not None and категория not in ai.КАТЕГОРИИ:
            raise StarletteHTTPException(400, "Такой категории нет.")
        return категория

    @app.get("/api/memory")
    def память():
        return база.память()

    @app.get("/api/memory/categories")
    def категории_памяти():
        return ai.КАТЕГОРИИ

    @app.post("/api/memory", status_code=201)
    def запомнить(факт: Факт):
        новый = база.запомнить(_непустой(факт.факт, "Факт"), None,
                               _проверить_категорию(факт.категория) or "другое", факт.важность or 3)
        if новый is None:
            raise StarletteHTTPException(400, "Такой факт уже есть в памяти.")
        return новый

    @app.patch("/api/memory/{fact_id}")
    def изменить_факт(fact_id: int, факт: Факт):
        поля = {}
        if факт.факт is not None:
            поля["факт"] = _непустой(факт.факт, "Факт")
        if факт.категория is not None:
            поля["категория"] = _проверить_категорию(факт.категория)
        if факт.важность is not None:
            поля["важность"] = факт.важность
        изменённый = база.изменить_факт(fact_id, поля)
        if изменённый is None:
            raise StarletteHTTPException(404, "Такого факта нет.")
        return изменённый

    # ---- Понимание: сущности, связи, цели --------------------------------------

    class Сущность(BaseModel):
        имя: str | None = Field(default=None, max_length=80)
        тип: str | None = None
        описание: str | None = Field(default=None, max_length=300)
        причина: str | None = Field(default=None, max_length=300)
        статус: str | None = None

    @app.get("/api/knowledge")
    def знания():
        return {"сущности": база.сущности(), "отношения": база.отношения(), "типы": ТИПЫ_СУЩНОСТЕЙ}

    @app.get("/api/knowledge/entity/{entity_id}")
    def карточка_сущности(entity_id: int):
        с = база.сущность(entity_id)
        if not с:
            raise StarletteHTTPException(404, "Такой сущности нет.")
        все = {х["id"]: х for х in база.сущности()}
        отношения = база.отношения()
        связи = []
        for о in отношения:
            if о["от_id"] == entity_id and о["к_id"] in все:
                связи.append({"id": о["id"], "куда": "→", "отношение": о["отношение"], "сущность": все[о["к_id"]]})
            elif о["к_id"] == entity_id and о["от_id"] in все:
                связи.append({"id": о["id"], "куда": "←", "отношение": о["отношение"], "сущность": все[о["от_id"]]})
        текст_ключ = lambda т: ключ_имени(т)
        задачи = [з for з in база.задачи() if з.get("цель_id") == entity_id
                  or memory._упомянута(с, текст_ключ(з["текст"]), текст_ключ(з["текст"]).split())]
        заметки = [з for з in база.заметки() if memory._упомянута(с, текст_ключ(з["текст"]), текст_ключ(з["текст"]).split())]
        return {
            "сущность": с,
            "связи": связи,
            "факты": [ф for ф in база.память() if entity_id in ф.get("сущности", [])],
            "задачи": задачи[:20],
            "заметки": заметки[:10],
            # упоминания в чате — с учётом падежей («у мамы» → «Мама»)
            "сообщения": [м for м in reversed(база.сообщения(1000))
                          if memory._упомянута(с, текст_ключ(м["текст"]), текст_ключ(м["текст"]).split())][:5],
            "цепочка": [{"отношение": о, "сущность": ц} for о, ц in memory.цепочка_причин(база, entity_id, отношения, все)],
        }

    @app.patch("/api/knowledge/entity/{entity_id}")
    def изменить_сущность(entity_id: int, изменение: Сущность):
        поля = {к: з for к, з in изменение.model_dump().items() if з is not None}
        if "тип" in поля and поля["тип"] not in ТИПЫ_СУЩНОСТЕЙ:
            raise StarletteHTTPException(400, "Такого типа нет.")
        if "статус" in поля and поля["статус"] not in ("", "активна", "достигнута", "отменена"):
            raise StarletteHTTPException(400, "Неверный статус цели.")
        if "имя" in поля:
            поля["имя"] = _непустой(поля["имя"], "Имя")
        с = база.изменить_сущность(entity_id, поля)
        if not с:
            raise StarletteHTTPException(404, "Такой сущности нет.")
        return с

    @app.delete("/api/knowledge/entity/{entity_id}")
    def удалить_сущность(entity_id: int):
        if not база.удалить_сущность(entity_id):
            raise StarletteHTTPException(404, "Такой сущности нет.")
        журнал.info("Сущность удалена из понимания.")
        return {"удалено": entity_id}

    @app.delete("/api/knowledge/relation/{relation_id}")
    def удалить_связь(relation_id: int):
        if not база.удалить_отношение(relation_id):
            raise StarletteHTTPException(404, "Такой связи нет.")
        return {"удалено": relation_id}

    @app.get("/api/goals")
    def цели():
        return база.цели()

    class НоваяЦель(BaseModel):
        имя: str = Field(max_length=80)
        почему: str = Field(default="", max_length=300)

    @app.post("/api/goals", status_code=201)
    def новая_цель(цель: НоваяЦель):
        с = база.сущность_или_новая(_непустой(цель.имя, "Цель"), "цель")
        if с["тип"] != "цель":
            с = база.изменить_сущность(с["id"], {"тип": "цель", "статус": "активна"})
        if цель.почему.strip():
            с = база.изменить_сущность(с["id"], {"причина": цель.почему.strip()})
        return с

    @app.get("/api/memory/working")
    def рабочая_память():
        сводка = база.сводка()
        return {"рабочая": база.прочитать("рабочая", {}), "сводка": сводка["текст"] if сводка else ""}

    @app.delete("/api/memory/working")
    def очистить_рабочую():
        база.очистить_разговор()
        return {"очищено": True}

    @app.delete("/api/memory/{fact_id}")
    def забыть(fact_id: int):
        if not база.забыть(fact_id):
            raise StarletteHTTPException(404, "Такого факта нет.")
        журнал.info("Факт удалён из памяти ИИ.")
        return {"удалено": fact_id}

    @app.delete("/api/memory")
    def забыть_всё():
        база.забыть_всё()
        журнал.info("Память ИИ очищена.")
        return {"очищено": True}

    @app.delete("/api/chat")
    def очистить_чат():
        база.очистить_чат()
        база.очистить_разговор()
        журнал.info("Чат очищен.")
        return {"очищено": True}

    # ---- ИИ: настройки cloud.ru --------------------------------------------
    # Ключ на страницу не отдаётся целиком — только последние 4 знака.

    def _для_страницы() -> dict:
        н = _ии()
        ключ = н["ключ"]
        return {
            **{к: з for к, з in н.items() if к != "ключ"},
            "есть_ключ": bool(ключ),
            "ключ_маска": f"••••{ключ[-4:]}" if len(ключ) > 8 else ("••••" if ключ else ""),
            "подключён": ai.подключён(н),
            "по_умолчанию": {к: з for к, з in ИИ_ПО_УМОЛЧАНИЮ.items() if к != "ключ"},
        }

    class ИзменениеИИ(BaseModel):
        ии: dict

    @app.get("/api/ai")
    def ии():
        return _для_страницы()

    @app.put("/api/ai")
    def изменить_ии(запрос_: ИзменениеИИ):
        новые = dict(запрос_.ии)
        if not новые.get("ключ"):
            новые.pop("ключ", None)           # пустое поле — оставить старый ключ
        if новые.pop("удалить_ключ", False):
            новые["ключ"] = ""
        try:
            проверено = проверить_ии({**_ии(), **новые}, строго=True)
        except НеверныйВнешнийВид as ошибка:
            raise StarletteHTTPException(400, str(ошибка))
        if проверено["включён"] and not (проверено["ключ"] and проверено["модель"]):
            raise StarletteHTTPException(400, "Чтобы включить ИИ, нужны ключ и модель.")
        настройки["ии"] = проверено
        сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
        журнал.info("Настройки ИИ сохранены (модель: %s, %s).", проверено["модель"] or "не выбрана",
                    "включён" if проверено["включён"] else "выключен")
        return _для_страницы()

    class ПроверкаКлюча(BaseModel):
        ключ: str | None = None
        адрес: str | None = None

    @app.post("/api/ai/models")
    def модели_ии(проверка: ПроверкаКлюча):
        """Список моделей по ключу — заодно проверка ключа. Пустой ключ — взять сохранённый."""
        ключ = (проверка.ключ or "").strip() or _ии()["ключ"]
        адрес = (проверка.адрес or "").strip() or _ии()["адрес"]
        try:
            модели = ai.список_моделей(адрес, ключ)
        except ai.ОшибкаИИ as ошибка:
            raise StarletteHTTPException(400, str(ошибка))
        журнал.info("Ключ cloud.ru работает, моделей: %s", len(модели))
        return {"модели": модели}

    @app.post("/api/ai/test")
    def проверить_ии_ответ():
        н = _ии()
        if not (н["ключ"] and н["модель"]):
            raise StarletteHTTPException(400, "Сначала сохраните ключ и модель.")
        try:
            return ai.проверить(н, настройки["имя"])
        except ai.ОшибкаИИ as ошибка:
            raise StarletteHTTPException(400, str(ошибка))

    # ---- Дела: задачи ---------------------------------------------------
    # Имена параметров в адресах — латиницей: кириллица в шаблоне пути не работает

    def _проверить_список(список_id: int | None) -> int | None:
        if список_id is not None and база.список(список_id) is None:
            raise StarletteHTTPException(400, "Такого списка нет.")
        return список_id

    def _проверить_цель(цель_id: int | None) -> int | None:
        if цель_id is not None:
            цель = база.сущность(цель_id)
            if not цель or цель["тип"] != "цель":
                raise StarletteHTTPException(400, "Такой цели нет.")
        return цель_id

    @app.get("/api/tasks")
    def задачи():
        return база.задачи()

    @app.post("/api/tasks", status_code=201)
    def новая_задача(задача: НоваяЗадача):
        новая = база.добавить_задачу(
            _непустой(задача.текст, "Текст задачи"),
            срок=_проверить_срок(задача.срок),
            список_id=_проверить_список(задача.список_id),
        )
        if задача.цель_id is not None:
            новая = база.изменить_задачу(новая["id"], {"цель_id": _проверить_цель(задача.цель_id)})
        return новая

    @app.post("/api/tasks/link-goals")
    def привязать_к_целям():
        н = _ии()
        if not ai.подключён(н):
            raise StarletteHTTPException(400, "Нужен подключённый ИИ (настройки проекта → ИИ).")
        try:
            return memory.привязать_задачи_к_целям(база, н)
        except ai.ОшибкаИИ as ошибка:
            raise StarletteHTTPException(400, str(ошибка))

    @app.patch("/api/tasks/{task_id}")
    def изменить_задачу(task_id: int, изменение: ИзменениеЗадачи):
        # Меняем только те поля, что пришли в запросе (null у срока/списка — убрать)
        пришло = изменение.model_fields_set
        поля = {}
        if "текст" in пришло:
            поля["текст"] = _непустой(изменение.текст, "Текст задачи")
        if "готово" in пришло and изменение.готово is not None:
            поля["готово"] = изменение.готово
        if "срок" in пришло:
            поля["срок"] = _проверить_срок(изменение.срок)
        if "список_id" in пришло:
            поля["список_id"] = _проверить_список(изменение.список_id)
        if "цель_id" in пришло:
            поля["цель_id"] = _проверить_цель(изменение.цель_id)
        задача = база.изменить_задачу(task_id, поля)
        if задача is None:
            raise StarletteHTTPException(404, "Такой задачи нет.")
        return задача

    @app.delete("/api/tasks/{task_id}")
    def удалить_задачу(task_id: int):
        if not база.удалить_задачу(task_id):
            raise StarletteHTTPException(404, "Такой задачи нет.")
        return {"удалено": task_id}

    # ---- Дела: списки задач ---------------------------------------------

    def _проверить_оформление(список: СписокЗадач) -> dict:
        поля = {}
        if список.название is not None:
            поля["название"] = _непустой(список.название, "Название списка")
        if список.цвет is not None:
            if список.цвет not in ЦВЕТА_СПИСКОВ:
                raise StarletteHTTPException(400, "Такого цвета нет.")
            поля["цвет"] = список.цвет
        if список.значок is not None:
            if список.значок not in ЗНАЧКИ_СПИСКОВ:
                raise StarletteHTTPException(400, "Такого значка нет.")
            поля["значок"] = список.значок
        return поля

    @app.get("/api/lists")
    def списки():
        return {"списки": база.списки(), "цвета": ЦВЕТА_СПИСКОВ, "значки": ЗНАЧКИ_СПИСКОВ}

    @app.post("/api/lists", status_code=201)
    def новый_список(список: СписокЗадач):
        поля = _проверить_оформление(список)
        if "название" not in поля:
            raise StarletteHTTPException(400, "Название списка не может быть пустым.")
        return база.добавить_список(поля["название"], поля.get("цвет", "серый"), поля.get("значок", "📋"))

    @app.patch("/api/lists/{list_id}")
    def изменить_список(list_id: int, список: СписокЗадач):
        изменённый = база.изменить_список(list_id, _проверить_оформление(список))
        if изменённый is None:
            raise StarletteHTTPException(404, "Такого списка нет.")
        return изменённый

    @app.delete("/api/lists/{list_id}")
    def удалить_список(list_id: int):
        if not база.удалить_список(list_id):
            raise StarletteHTTPException(404, "Такого списка нет.")
        return {"удалено": list_id}

    # ---- Дела: заметки --------------------------------------------------

    @app.get("/api/notes")
    def заметки():
        return база.заметки()

    @app.post("/api/notes", status_code=201)
    def новая_заметка(заметка: Текст):
        return база.добавить_заметку(_непустой(заметка.текст, "Заметка"))

    @app.patch("/api/notes/{note_id}")
    def изменить_заметку(note_id: int, заметка: Текст):
        изменённая = база.изменить_заметку(note_id, _непустой(заметка.текст, "Заметка"))
        if изменённая is None:
            raise StarletteHTTPException(404, "Такой заметки нет.")
        return изменённая

    @app.delete("/api/notes/{note_id}")
    def удалить_заметку(note_id: int):
        if not база.удалить_заметку(note_id):
            raise StarletteHTTPException(404, "Такой заметки нет.")
        return {"удалено": note_id}

    # ---- Работа: сотрудники, автомобили, ГСМ, табель, записки, договоры ---------
    work.подключить(app, база)

    # ---- Агенты: кто сейчас работает, сколько раз сегодня ----------------------
    agents.подключить(база)

    @app.get("/api/agents")
    def агенты():
        return agents.сводка()

    def _агент(ключ: str) -> str:
        if ключ not in agents.ИМЕНА:
            raise StarletteHTTPException(404, "Такого агента нет.")
        return ключ

    @app.get("/api/agents/board")
    def доска_агентов():
        return {"записки": agents.доска(), "имена": agents.ИМЕНА}

    class Записка(BaseModel):
        кому: str
        текст: str = Field(max_length=300)

    @app.post("/api/agents/board", status_code=201)
    def написать_агенту(записка: Записка):
        кому = записка.кому if записка.кому == "все" else _агент(записка.кому)
        return agents.написать("вы", кому, _непустой(записка.текст, "Записка"))

    @app.delete("/api/agents/board")
    def очистить_доску():
        agents.очистить_доску()
        return {"очищено": True}

    @app.get("/api/agents/{agent}")
    def агент(agent: str, q: str = "", limit: int = Query(50, ge=1, le=500)):
        ключ = _агент(agent)
        сводка = next(а for а in agents.сводка()["агенты"] if а["ключ"] == ключ)
        return {**сводка, "история": agents.история(ключ, q, limit), "заметки": agents.заметки(ключ),
                "записки": agents.доска(ключ, 40), "имена": agents.ИМЕНА}

    class ЗаметкаАгента(BaseModel):
        вид: str
        текст: str = Field(max_length=300)

    @app.post("/api/agents/{agent}/notes", status_code=201)
    def заметка_агенту(agent: str, заметка: ЗаметкаАгента):
        ключ = _агент(agent)
        if заметка.вид not in ("правило", "приём"):
            raise StarletteHTTPException(400, "Можно добавить правило или приём.")
        return agents.добавить_заметку(ключ, заметка.вид, _непустой(заметка.текст, "Заметка"))

    @app.delete("/api/agents/notes/{note_id}")
    def удалить_заметку_агента(note_id: int):
        if not agents.удалить_заметку(note_id):
            raise StarletteHTTPException(404, "Такой заметки нет.")
        return {"удалено": note_id}

    # ---- Душа ------------------------------------------------------------
    # Характер и ценности ИИ; настроение считается из дел и разговоров.

    def _душа() -> dict:
        return {
            "имя": настройки["имя"],
            "душа": soul.прочитать(база),
            "настроение": soul.настроение(база),
            "знакомство": soul.знакомство(база),
            "мнения": soul.прочитать_мнения(база),
            "развитие": soul.прочитать_развитие(база),
            "важное": soul.важное(база),
            "ии": ai.подключён(_ии()),
            "по_умолчанию": soul.ДУША_ПО_УМОЛЧАНИЮ,
        }

    @app.get("/api/soul")
    def душа():
        return _душа()

    class ИзменениеДуши(BaseModel):
        душа: dict

    @app.put("/api/soul")
    def изменить_душу(запрос_: ИзменениеДуши):
        try:
            soul.сохранить(база, запрос_.душа)
        except soul.НевернаяДуша as ошибка:
            raise StarletteHTTPException(400, str(ошибка))
        журнал.info("Душа ИИ изменена.")
        return _душа()

    @app.post("/api/soul/opinions")
    def обновить_мнения():
        н = _ии()
        if not ai.подключён(н):
            raise StarletteHTTPException(400, "Чтобы душа высказала мнения, подключите ИИ в настройках.")
        try:
            soul.обновить_мнения(база, н)
        except ai.ОшибкаИИ as ошибка:
            raise StarletteHTTPException(502, f"ИИ не ответил: {ошибка}")
        return _душа()

    class НастройкиРазвития(BaseModel):
        включено: bool

    @app.put("/api/soul/development")
    def настроить_фоновое_развитие(запрос_: НастройкиРазвития):
        soul.настроить_развитие(база, запрос_.включено)
        журнал.info("Фоновое развитие Души: %s.", "включено" if запрос_.включено else "выключено")
        return _душа()

    class УбратьМнение(BaseModel):
        о: str

    @app.post("/api/soul/opinions/remove")
    def убрать_мнение(запрос_: УбратьМнение):
        if not soul.убрать_мнение(база, запрос_.о):
            raise StarletteHTTPException(404, "Такого мнения нет.")
        return _душа()

    @app.delete("/api/soul")
    def сбросить_душу():
        soul.сбросить(база)
        журнал.info("Душа ИИ сброшена к исходной.")
        return _душа()

    # ---- Мозги -----------------------------------------------------------
    # Всё, что знает Mizuyori, одним запросом: из этого сайт строит граф.

    @app.get("/api/brain")
    def мозги():
        return {
            "имя": настройки["имя"],
            "задачи": база.задачи(),
            "списки": база.списки(),
            "цвета": ЦВЕТА_СПИСКОВ,
            "заметки": база.заметки(),
            "сообщения": база.сообщения(500),
            "память": база.память(),
            "рабочая": база.прочитать("рабочая", {}),
            "сущности": база.сущности(),
            "отношения": база.отношения(),
            "настройки": настройки["мозги"],
            "по_умолчанию": МОЗГИ_ПО_УМОЛЧАНИЮ,
        }

    # Смысловые связи: эмбеддинги cloud.ru → похожесть по косинусу.
    # Вектора считаются один раз и хранятся в базе; пересчёт — только изменённых текстов.
    @app.get("/api/brain/links")
    def смысловые_связи(порог: float = Query(0.75, alias="threshold"), соседей: int = Query(3, alias="k")):
        import numpy as np

        н = _ии()
        модель = н["модель_эмбеддингов"]
        if not н["ключ"]:
            return {"доступно": False, "причина": "Нужен ключ cloud.ru (настройки проекта → ИИ)."}
        if not модель:
            return {"доступно": False, "причина": "Выберите модель для связей (настройки проекта → ИИ)."}

        тексты: dict[str, str] = {}
        for з in база.задачи():
            тексты[f"з{з['id']}"] = з["текст"]
        for з in база.заметки():
            тексты[f"н{з['id']}"] = з["текст"][:4000]
        for ф in база.память():
            тексты[f"п{ф['id']}"] = ф["факт"]
        for с in база.сущности():
            тексты[f"е{с['id']}"] = f"{с['имя']} ({с['тип']}): {с['описание']} {с['причина']}".strip()
        if len(тексты) < 2:
            return {"доступно": True, "связи": [], "модель": модель, "новых": 0}
        try:
            ключи, матрица, новых = memory.обеспечить_вектора(база, н, тексты)
        except ai.ОшибкаИИ as ошибка:
            return {"доступно": False, "причина": str(ошибка)}
        if новых:
            журнал.info("Смысловые вектора посчитаны: %s", новых)
        база.убрать_лишние_вектора(set(тексты))
        if len(ключи) < 2:
            return {"доступно": True, "связи": [], "модель": модель, "новых": новых}
        похожесть = матрица @ матрица.T
        np.fill_diagonal(похожесть, -1)
        соседей = max(1, min(соседей, 10))
        пары = {}
        for i in range(len(ключи)):
            for j in np.argsort(-похожесть[i])[:соседей]:
                п = float(похожесть[i, j])
                if п < порог:
                    break
                а, б = sorted((ключи[i], ключи[int(j)]))
                пары[(а, б)] = round(п, 3)
        связи = [{"а": а, "б": б, "похожесть": п} for (а, б), п in sorted(пары.items(), key=lambda x: -x[1])]
        return {"доступно": True, "связи": связи, "модель": модель, "новых": новых}

    class НастройкиМозгов(BaseModel):
        мозги: dict

    @app.put("/api/brain/settings")
    def сохранить_мозги(запрос_: НастройкиМозгов):
        try:
            новые = проверить_мозги(запрос_.мозги, строго=True)
        except НеверныйВнешнийВид as ошибка:
            raise StarletteHTTPException(400, str(ошибка))
        настройки["мозги"] = новые
        сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
        журнал.info("Настройки мозгов сохранены.")
        return новые

    soul.запустить_фоновое_развитие(
        база, _ии, lambda: последняя_активность[0]
    )
    return app
