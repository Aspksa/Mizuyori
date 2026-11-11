"""Веб-сервер: страница и API."""

import json
import logging
import platform
from datetime import date
from html import escape

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, ai
from .config import (ВИД_ПО_УМОЛЧАНИЮ, ВНЕШНИЙ_ВИД, ИИ_ПО_УМОЛЧАНИЮ, МОЗГИ_ПО_УМОЛЧАНИЮ,
                     НеверныйВнешнийВид, атрибуты_html, проверить_внешний_вид, проверить_ии,
                     проверить_мозги, сохранить_настройки)
from .database import База
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


class ИзменениеЗадачи(BaseModel):
    текст: str | None = Field(default=None, max_length=2000)
    готово: bool | None = None
    срок: str | None = None
    список_id: int | None = None


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
                for кусок in ai.ответ_потоком(история, н, настройки["имя"]):
                    собрано.append(кусок)
                    yield строка({"кусок": кусок})
            except ai.ОшибкаИИ as ошибка:
                журнал.warning("ИИ не ответил: %s", ошибка)
                yield строка({"ошибка": str(ошибка)})
                return
            except Exception:
                журнал.exception("ИИ не смог ответить")
                yield строка({"ошибка": "Непредвиденная ошибка ИИ. Подробности в logs/mizuyori.log."})
                return
            ответ = ai.убрать_размышления("".join(собрано)) or "…"
            yield строка({"ответ": база.добавить_сообщение("ии", ответ)})

        return StreamingResponse(поток(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.delete("/api/chat")
    def очистить_чат():
        база.очистить_чат()
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

    @app.get("/api/tasks")
    def задачи():
        return база.задачи()

    @app.post("/api/tasks", status_code=201)
    def новая_задача(задача: НоваяЗадача):
        return база.добавить_задачу(
            _непустой(задача.текст, "Текст задачи"),
            срок=_проверить_срок(задача.срок),
            список_id=_проверить_список(задача.список_id),
        )

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
            "настройки": настройки["мозги"],
            "по_умолчанию": МОЗГИ_ПО_УМОЛЧАНИЮ,
        }

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

    return app
