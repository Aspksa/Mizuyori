"""Веб-сервер: страница и API."""

import json
import logging
import platform
import threading
import time
from datetime import date
from html import escape
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import (__version__, agents, ai, archive, audit, browser_fetch, documents, evolve, graph_tools, learning, memory, memory_plus, missions, printing, putevoy,
               search_eval, senses, smeta, soul, tools, work, work_agents)
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
    приоритет: str = "обычный"
    повтор: str = ""
    входящие: bool = False


class ИзменениеЗадачи(BaseModel):
    текст: str | None = Field(default=None, max_length=2000)
    готово: bool | None = None
    срок: str | None = None
    список_id: int | None = None
    цель_id: int | None = None
    приоритет: str | None = None
    повтор: str | None = None
    входящие: bool | None = None
    архив: bool | None = None


class НастройкиДел(BaseModel):
    первый_день: str = "понедельник"
    рабочие_дни: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])


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

    def _запомнить_замену(адрес: str, было: str, стало: str) -> None:
        н = настройки["ии"]
        if н.get("модель_эмбеддингов") == было:
            н["модель_эмбеддингов"] = стало
            сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
    ai.при_замене_модели = _запомнить_замену

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
            агент_работы = сообщение_печати = ""
            learning.чат_идёт()
            try:
                learning.проверить_поправку(текст)      # «нет, не так» — агент учится на поправке
            except Exception:
                журнал.exception("Поправка агенту не записалась")
            try:
                р = work_agents.для_чата(база, н, текст)
                if р:
                    контекст["работа"] = р["текст"]
                    if р.get("правила"):
                        контекст["правила"] = f"{контекст.get('правила') or ''}\n{р['правила']}".strip()
                    агент_работы = р.get("агент") or ""
                    сообщение_печати = р.get("сообщение") or ""
            except Exception:
                журнал.exception("Агенты Работы не смогли подключиться к чату")
            try:
                with agents.работа("чат", "ответил в чате", f"вы написали: «{' '.join(текст.split())[:60]}»") as запись:
                    for кусок in ai.ответ_потоком(история, н, настройки["имя"], контекст):
                        собрано.append(кусок)
                        yield строка({"кусок": кусок})
                    м, о = ai.отделить_мысль(ai.убрать_размышления("".join(собрано)))
                    запись["результат"] = f"ответ {len(о)} знаков" + (" · с мыслью" if м else "")
                    запись["польза"] = 1
                if агент_работы:
                    with agents.работа(агент_работы, "ответил в чате", f"вы обратились: «{' '.join(текст.split())[:60]}»") as з:
                        з["результат"] = "ответ в чате"
                        з["польза"] = 1
            except ai.ОшибкаИИ as ошибка:
                журнал.warning("ИИ не ответил: %s", ошибка)
                yield строка({"ошибка": str(ошибка)})
                return
            except Exception:
                журнал.exception("ИИ не смог ответить")
                yield строка({"ошибка": "Непредвиденная ошибка ИИ. Подробности в logs/mizuyori.log."})
                return
            мысль, ответ = ai.отделить_мысль(ai.убрать_размышления("".join(собрано)))
            if агент_работы:
                learning.запомнить_обмен(агент_работы, текст, ответ)
            if сообщение_печати:      # итог печати — от системы, а не со слов ИИ
                ответ = f"{ответ}\n\n{сообщение_печати}".strip()
            yield строка({"ответ": база.добавить_сообщение("ии", ответ or "…", мысль)})
            # Память и сводка — в фоне, чтобы не задерживать ответ
            threading.Thread(target=memory.после_ответа, args=(база, н, текст, ответ, вопрос["id"]),
                             daemon=True).start()

        return StreamingResponse(поток(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.post("/api/chat/attach")
    async def вложение(request: Request, name: str = Query("файл", max_length=200)):
        """Файл в чат (сырые байты в теле): смета на ремонт → разбор → сообщение агента с проверкой."""
        данные = await request.body()
        if not данные:
            raise StarletteHTTPException(400, "Файл пустой.")
        н = dict(_ии())
        мой = база.добавить_сообщение("пользователь", f"📎 {name}")
        learning.чат_идёт()
        try:
            инфо = await run_in_threadpool(archive.опознать, база, н, name, данные)
            if инфо["вид"] not in ("Смета", "Коммерческое предложение", "Прочее"):
                with agents.работа("архивариус", "рассмотрел вложение", f"файл «{name}»") as з:
                    ф = await run_in_threadpool(archive.принять_файл, база, н, name, данные)
                    з["результат"] = f"{инфо['вид']}: {ф.get('путь') or name}"
                    з["польза"] = 2
                return {"вы": мой, "ответ": база.добавить_сообщение(
                    "ии", f"👁 Это «{инфо['вид'].lower()}» — Архивариус положил в архив: {ф.get('путь') or name}")}
            if not ai.подключён(н):
                raise smeta.СметаНеЧитается("Чтобы разобрать смету, нужен подключённый ИИ (настройки проекта → ИИ).")
            from .smeta import принять
            with agents.работа("инженер", "разобрал смету", f"файл «{name}»") as з:
                с = await run_in_threadpool(принять, база, н, name, данные)
                з["результат"] = f"позиций: {len(с['позиции'])}, замечаний: {len(с['замечания'])}"
                з["польза"] = 3
            текст = smeta.описание(с)
        except smeta.СметаНеЧитается as ошибка:
            текст = f"📎 {ошибка}"
        except Exception as ошибка:
            журнал.exception("Смета не разобралась")
            текст = f"📎 Не получилось разобрать «{name}»: {ошибка}"
        return {"вы": мой, "ответ": база.добавить_сообщение("ии", текст)}

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
                               _проверить_категорию(факт.категория) or "другое", факт.важность or 3,
                               уверенность=1.0)
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

    @app.get("/api/memory/plus")
    def память_порядок():
        return {"подтверждение": memory_plus.нужно_подтверждение(база), "предложения": memory_plus.предложения(база),
                "архив": memory_plus.архив(база)}

    class Подтверждение(BaseModel):
        да: bool

    @app.put("/api/memory/confirmation")
    def память_подтверждение(п: Подтверждение):
        memory_plus.включить_подтверждение(база, п.да)
        audit.записать("память: спрашивать перед запоминанием", "включено" if п.да else "выключено")
        return {"подтверждение": п.да}

    @app.post("/api/memory/proposals/{proposal_id}/accept")
    def принять_в_память(proposal_id: int):
        итог = memory_plus.принять(база, proposal_id)
        if not итог:
            raise StarletteHTTPException(404, "Предложение уже решено или не найдено.")
        return итог

    @app.post("/api/memory/proposals/{proposal_id}/reject")
    def отклонить_в_память(proposal_id: int):
        итог = memory_plus.отклонить(база, proposal_id)
        if not итог:
            raise StarletteHTTPException(404, "Предложение уже решено или не найдено.")
        return итог

    @app.post("/api/memory/{fact_id}/restore")
    def вернуть_из_архива(fact_id: int):
        итог = memory_plus.восстановить(база, fact_id)
        if not итог:
            raise StarletteHTTPException(404, "Факта нет в архиве.")
        audit.записать("факт возвращён из архива", итог["факт"][:100])
        return итог

    @app.get("/api/memory/{fact_id}/history")
    def история_факта(fact_id: int):
        return {"версии": memory_plus.история_факта(база, fact_id)}

    @app.post("/api/memory/sleep")
    def навести_порядок():
        return memory_plus.сон(база, dict(_ии()))

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

    def _проверить_приоритет(приоритет: str | None) -> str:
        if приоритет not in ("срочный", "высокий", "обычный", "низкий"):
            raise StarletteHTTPException(400, "Неизвестный приоритет задачи.")
        return приоритет

    def _проверить_повтор(повтор: str | None) -> str:
        if повтор not in ("", "день", "будни", "неделя", "месяц"):
            raise StarletteHTTPException(400, "Неизвестный режим повторения.")
        return повтор

    @app.get("/api/tasks")
    def задачи(view: str = "active"):
        виды = {"active": "активные", "archive": "архив", "trash": "корзина", "all": "все"}
        if view not in виды:
            raise StarletteHTTPException(400, "Неизвестный вид задач.")
        return база.задачи(виды[view])

    @app.post("/api/tasks", status_code=201)
    def новая_задача(задача: НоваяЗадача):
        новая = база.добавить_задачу(
            _непустой(задача.текст, "Текст задачи"),
            срок=_проверить_срок(задача.срок),
            список_id=_проверить_список(задача.список_id),
            приоритет=_проверить_приоритет(задача.приоритет),
            повтор=_проверить_повтор(задача.повтор),
            входящие=задача.входящие,
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

    @app.get("/api/tasks/settings")
    def настройки_дел():
        сохранено = база.прочитать("настройки_дел", {}) or {}
        return {"первый_день": сохранено.get("первый_день", "понедельник"),
                "рабочие_дни": сохранено.get("рабочие_дни", [1, 2, 3, 4, 5])}

    @app.put("/api/tasks/settings")
    def сохранить_настройки_дел(новые: НастройкиДел):
        if новые.первый_день not in ("понедельник", "воскресенье"):
            raise StarletteHTTPException(400, "Неделя может начинаться с понедельника или воскресенья.")
        рабочие = sorted(set(новые.рабочие_дни))
        if not рабочие or any(д < 1 or д > 7 for д in рабочие):
            raise StarletteHTTPException(400, "Выберите хотя бы один рабочий день.")
        итог = {"первый_день": новые.первый_день, "рабочие_дни": рабочие}
        база.записать("настройки_дел", итог)
        return итог

    @app.post("/api/tasks/archive-completed")
    def архивировать_выполненные():
        return {"архивировано": база.архивировать_выполненные()}

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
        if "приоритет" in пришло and изменение.приоритет is not None:
            поля["приоритет"] = _проверить_приоритет(изменение.приоритет)
        if "повтор" in пришло and изменение.повтор is not None:
            поля["повтор"] = _проверить_повтор(изменение.повтор)
        if "входящие" in пришло and изменение.входящие is not None:
            поля["входящие"] = изменение.входящие
        if "архив" in пришло and изменение.архив is not None:
            поля["архив"] = изменение.архив
        задача = база.изменить_задачу(task_id, поля)
        if задача is None:
            raise StarletteHTTPException(404, "Такой задачи нет.")
        return задача

    @app.post("/api/tasks/{task_id}/restore")
    def восстановить_задачу(task_id: int):
        задача = база.восстановить_задачу(task_id)
        if задача is None:
            raise StarletteHTTPException(404, "Такой задачи нет.")
        return задача

    @app.delete("/api/tasks/{task_id}")
    def удалить_задачу(task_id: int, permanent: bool = False):
        if not база.удалить_задачу(task_id, навсегда=permanent):
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
    work_agents.зарегистрировать()
    missions.подключить(база)
    audit.подключить(база)
    tools.подключить(lambda: база.прочитать("инструменты", {}), lambda з: база.записать("инструменты", з))
    browser_fetch.настроить(настройки["агенты"].get("браузер_для_поиска", ""))
    missions.заполнить_готовые()
    printing.НАСТРОЙКИ = настройки["печать"]
    learning.НАСТРОЙКИ = настройки["агенты"]
    documents.НАСТРОЙКИ = настройки["агенты"]

    @app.get("/api/agents-learning")
    def учёба_агентов():
        return learning.состояние()

    @app.get("/api/agents-learning/review")
    def ревизия_учёбы():
        return {"приёмы": learning.ревизия()}

    @app.post("/api/agents/notes/{note_id}/keep")
    def оставить_приём(note_id: int):
        if not agents.оставить_навсегда(note_id):
            raise StarletteHTTPException(404, "Такого приёма нет.")
        return {"оставлено": note_id}

    class ВидЗаметки(BaseModel):
        вид: str

    @app.put("/api/agents/notes/{note_id}")
    def вид_заметки(note_id: int, з: ВидЗаметки):
        if not agents.изменить_вид(note_id, з.вид):
            raise StarletteHTTPException(404, "Записи нет или она уже такого вида.")
        return {"изменено": note_id, "вид": з.вид}

    class КомуЗнание(BaseModel):
        кому: str

    @app.post("/api/agents/notes/{note_id}/share")
    def передать_знание(note_id: int, з: КомуЗнание):
        итог = agents.передать_знание(note_id, _агент(з.кому))
        if not итог:
            raise StarletteHTTPException(404, "Записи нет, или её нельзя передать этому агенту.")
        return итог

    class УчёбаПереключатель(BaseModel):
        включено: bool | None = None
        запросов_в_час: int | None = Field(None, ge=1, le=200)

    @app.put("/api/agents-learning")
    def настроить_учёбу(з: УчёбаПереключатель):
        if з.включено is not None:
            настройки["агенты"]["учиться_в_фоне"] = з.включено
        if з.запросов_в_час is not None:
            настройки["агенты"]["запросов_в_час"] = з.запросов_в_час
        сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
        return learning.состояние()

    @app.get("/api/agents")
    def агенты(days: int = Query(7, ge=7, le=90)):
        return agents.сводка(days)

    def _агент(ключ: str) -> str:
        if ключ not in agents.ИМЕНА:
            raise StarletteHTTPException(404, "Такого агента нет.")
        return ключ

    @app.get("/api/agents/knowledge")
    def знания_агентов(q: str = Query("", max_length=100), limit: int = Query(200, ge=1, le=500)):
        return {"знания": agents.все_знания(q, limit)}

    @app.get("/api/agents/knowledge/audit")
    def проверка_знаний():
        return agents.проверить_знания()

    @app.get("/api/agents/exchange")
    def обмен_агентов(limit: int = Query(60, ge=1, le=200)):
        return agents.обмен(limit)

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
                "записки": agents.доска(ключ, 40), "имена": agents.ИМЕНА,
                "уроки_недели": agents.выучено(ключ, 7), "профиль": agents.профиль(ключ),
                "подсказка": agents.правила(ключ),
                "навыки": agents.навыки(ключ), "версии": agents.версии(ключ),
                "качество": evolve.качество(ключ), "предложения": evolve.предложения(ключ, 10)}

    class ПрофильАгента(BaseModel):
        роль: str = Field("", max_length=agents.ПРЕДЕЛ_ПОЛЯ)
        цель: str = Field("", max_length=agents.ПРЕДЕЛ_ПОЛЯ)
        предыстория: str = Field("", max_length=agents.ПРЕДЕЛ_ПОЛЯ)
        указания: str = Field("", max_length=agents.ПРЕДЕЛ_ПОЛЯ)

    @app.put("/api/agents/{agent}/profile")
    def профиль_агента(agent: str, п: ПрофильАгента):
        ключ = _агент(agent)
        итог = {"профиль": agents.сохранить_профиль(ключ, п.model_dump()), "подсказка": agents.правила(ключ)}
        audit.записать("профиль агента изменён", agents.ИМЕНА[ключ], "; ".join(f"{к}: {з[:40]}" for к, з in итог["профиль"].items() if з))
        return {**итог, "версии": agents.версии(ключ)}

    class НавыкАгента(BaseModel):
        название: str = Field("", max_length=80)
        когда: str = Field("", max_length=200)
        текст: str = Field("", max_length=agents.ПРЕДЕЛ_НАВЫКА)
        включён: bool = True

    @app.post("/api/agents/{agent}/skills", status_code=201)
    def новый_навык(agent: str, н: НавыкАгента):
        ключ = _агент(agent)
        try:
            итог = agents.добавить_навык(ключ, н.название, н.когда, н.текст)
        except ValueError as е:
            raise StarletteHTTPException(400, str(е)) from None
        audit.записать("навык добавлен", f"{agents.ИМЕНА[ключ]}: {итог['название']}", итог["когда"])
        return итог

    @app.put("/api/agents/skills/{skill_id}")
    def изменить_навык(skill_id: int, н: НавыкАгента):
        итог = agents.изменить_навык(skill_id, н.model_dump())
        if not итог:
            raise StarletteHTTPException(404, "Такого навыка нет.")
        audit.записать("навык изменён", f"{agents.ИМЕНА.get(итог['агент'], итог['агент'])}: {итог['название']}",
                       "включён" if итог["включён"] else "выключен")
        return итог

    @app.delete("/api/agents/skills/{skill_id}")
    def удалить_навык(skill_id: int):
        if not agents.удалить_навык(skill_id):
            raise StarletteHTTPException(404, "Такого навыка нет.")
        audit.записать("навык удалён", f"№{skill_id}")
        return {"удалено": skill_id}

    @app.post("/api/agents/versions/{version_id}/rollback")
    def откатить_агента(version_id: int):
        итог = agents.откатить(version_id)
        if not итог:
            raise StarletteHTTPException(404, "Такой версии нет.")
        audit.записать("откат агента", agents.ИМЕНА.get(итог["агент"], итог["агент"]), f"к версии {итог['к_версии']}")
        return {**итог, "версии": agents.версии(итог["агент"])}

    @app.get("/api/agents/{agent}/quality")
    def качество_агента(agent: str):
        return evolve.качество(_агент(agent))

    @app.post("/api/agents/{agent}/improve")
    def улучшить_агента(agent: str):
        ключ = _агент(agent)
        try:
            return evolve.разобрать_неудачи(ключ, _ии())
        except Exception as е:
            raise StarletteHTTPException(502, f"Не удалось разобрать: {е}") from None

    @app.post("/api/agents/proposals/{proposal_id}/accept")
    def принять_улучшение(proposal_id: int):
        итог = evolve.принять_предложение(proposal_id)
        if not итог:
            raise StarletteHTTPException(404, "Предложение уже решено или не найдено.")
        return {"предложение": итог, "версии": agents.версии(итог["агент"])}

    @app.post("/api/agents/proposals/{proposal_id}/reject")
    def отклонить_улучшение(proposal_id: int):
        итог = evolve.отклонить_предложение(proposal_id)
        if not итог:
            raise StarletteHTTPException(404, "Предложение уже решено или не найдено.")
        return {"предложение": итог}

    @app.get("/api/tools")
    def инструменты():
        return {"инструменты": tools.список(), "настройки": tools.настройки(), "наборы": sorted(tools.наборы())}

    class НастройкиИнструментов(BaseModel):
        только_чтение: bool | None = None
        выключены: list[str] | None = None
        агенты: dict[str, list[str]] | None = None

    @app.put("/api/tools/settings")
    def настроить_инструменты(н: НастройкиИнструментов):
        новые = {к: з for к, з in н.model_dump().items() if з is not None}
        итог = tools.сохранить_настройки(новые)
        audit.записать("настройки инструментов изменены", "только чтение" if итог["только_чтение"] else "обычный режим",
                       f"выключены наборы: {', '.join(итог['выключены']) or 'нет'}")
        return {"настройки": итог}

    @app.get("/api/search-eval")
    def история_проверки_поиска():
        return {"прогоны": search_eval.история(12), "запросов": len(search_eval.НАБОР)}

    @app.post("/api/search-eval/run")
    def проверить_поиск():
        итог = search_eval.прогнать()
        audit.записать("проверка поиска", итог["вердикт"], f"{итог['балл']:.0%}, ошибок {итог['ошибок']}")
        return итог

    @app.get("/api/audit")
    def журнал_аудита(q: str = "", limit: int = Query(100, ge=1, le=500)):
        return {"записи": audit.список(limit, q)}

    class ЗаметкаАгента(BaseModel):
        вид: str
        текст: str = Field(max_length=300)

    @app.post("/api/agents/{agent}/notes", status_code=201)
    def заметка_агенту(agent: str, заметка: ЗаметкаАгента):
        ключ = _агент(agent)
        if заметка.вид not in ("правило", "приём"):
            raise StarletteHTTPException(400, "Можно добавить правило или приём.")
        итог = agents.добавить_заметку(ключ, заметка.вид, _непустой(заметка.текст, "Заметка"))
        audit.записать(f"{заметка.вид} добавлено", agents.ИМЕНА[ключ], заметка.текст)
        return итог

    @app.delete("/api/agents/notes/{note_id}")
    def удалить_заметку_агента(note_id: int):
        if not agents.удалить_заметку(note_id):
            raise StarletteHTTPException(404, "Такой заметки нет.")
        audit.записать("заметка агента удалена", f"№{note_id}")
        return {"удалено": note_id}

    # ---- Поручения: шаги, проверка, подтверждение, шаблоны, руководитель -------------------------

    def _поручение(действие):
        try:
            return действие()
        except missions.ОшибкаПоручения as е:
            raise StarletteHTTPException(400, str(е)) from None

    class ШагПоручения(BaseModel):
        агент: str
        описание: str = Field(max_length=2000)
        ожидание: str = Field("", max_length=600)
        инструмент: str = ""
        проверяющий: str = ""
        подтверждать: bool = False

    class НовоеПоручение(BaseModel):
        название: str = Field(max_length=120)
        шаги: list[ШагПоручения]
        параметры: dict[str, str] = {}
        режим: str = "по порядку"
        запустить: bool = True

    class ЦельПоручения(BaseModel):
        цель: str = Field(max_length=500)
        запустить: bool = True

    class НовыйШаблон(BaseModel):
        название: str = Field(max_length=120)
        шаги: list[ШагПоручения]
        режим: str = "по порядку"

    @app.get("/api/missions")
    def поручения():
        исполнители = [{"ключ": к, "имя": и} for к, и in agents.ИМЕНА.items() if к != "смысл"]
        return {"поручения": missions.список(), "шаблоны": missions.шаблоны(), "инструменты": tools.список(),
                "агенты": исполнители, "ии": ai.подключён(_ии())}

    @app.post("/api/missions", status_code=201)
    def новое_поручение(п: НовоеПоручение):
        def сделать():
            м = missions.создать(п.название, [ш.model_dump() for ш in п.шаги], п.параметры, п.режим)
            return missions.запустить(м["id"], dict(_ии())) if п.запустить else м
        return _поручение(сделать)

    @app.post("/api/missions/plan", status_code=201)
    def спланировать_поручение(ц: ЦельПоручения):
        def сделать():
            м = missions.спланировать(ц.цель, dict(_ии()))
            return missions.запустить(м["id"], dict(_ии())) if ц.запустить else м
        return _поручение(сделать)

    @app.post("/api/missions/templates", status_code=201)
    def новый_шаблон(ш: НовыйШаблон):
        итог = _поручение(lambda: missions.сохранить_шаблон(ш.название, [х.model_dump() for х in ш.шаги], ш.режим))
        audit.записать("шаблон поручения сохранён", ш.название)
        return итог

    @app.delete("/api/missions/templates/{template_id}")
    def удалить_шаблон(template_id: int):
        if not missions.удалить_шаблон(template_id):
            raise StarletteHTTPException(404, "Такого шаблона нет.")
        audit.записать("шаблон поручения удалён", f"№{template_id}")
        return {"удалено": template_id}

    @app.get("/api/missions/{mission_id}")
    def одно_поручение(mission_id: int):
        м = missions.получить(mission_id)
        if not м:
            raise StarletteHTTPException(404, "Такого поручения нет.")
        return м

    @app.post("/api/missions/{mission_id}/run")
    def запустить_поручение(mission_id: int):
        return _поручение(lambda: missions.запустить(mission_id, dict(_ии())))

    @app.post("/api/missions/{mission_id}/confirm")
    def подтвердить_поручение(mission_id: int, отпечаток: str = Query("", max_length=40)):
        return _поручение(lambda: missions.подтвердить(mission_id, dict(_ии()), отпечаток))

    @app.post("/api/missions/{mission_id}/reject")
    def отклонить_поручение(mission_id: int):
        return _поручение(lambda: missions.отклонить(mission_id))

    @app.delete("/api/missions/{mission_id}")
    def удалить_поручение(mission_id: int):
        if not _поручение(lambda: missions.удалить(mission_id)):
            raise StarletteHTTPException(404, "Такого поручения нет.")
        return {"удалено": mission_id}

    # ---- Агенты «Работы»: замечания, обход, служебные записки -----------------------------

    @app.get("/api/work-agents")
    def агенты_работы():
        свод = {а["ключ"]: а for а in agents.сводка()["агенты"]}
        итог = []
        for а in work_agents.РАБОЧИЕ_АГЕНТЫ:
            try:
                з = work_agents.замечания(база, а["ключ"])
            except Exception:
                журнал.exception("Агент %s не смог посмотреть данные", а["ключ"])
                з = []
            итог.append({**свод[а["ключ"]], "замечания": sorted(з, key=lambda н: -н["важно"])})
        return {"агенты": итог, "ии_подключён": ai.подключён(_ии())}

    @app.post("/api/work-agents/{agent}/run")
    def обойти_агента(agent: str):
        if agent not in work_agents.КЛЮЧИ:
            raise StarletteHTTPException(404, "Такого агента нет.")
        нашёл = work_agents.обойти(база, agent)
        try:
            учёба = work_agents.научиться(база, agent, agents.с_правилами(dict(_ии()), agent))
        except Exception:
            журнал.exception("Агент %s не смог научиться (ИИ недоступен?)", agent)
            учёба = ""
        return {"замечаний": len([н for н in нашёл if н["важно"] >= 1]), "новый_приём": учёба}

    class ЗаписокЗапрос(BaseModel):
        тема: str = Field(max_length=200)
        пояснение: str = Field("", max_length=1500)
        кому: str = Field("", max_length=200)
        от_кого: str = Field("", max_length=200)

    @app.get("/api/work-agents/putevoy/{name}")
    def готовый_путевой(name: str):
        файл = putevoy.ПАПКА_ГОТОВЫХ / Path(name).name
        if not файл.is_file():
            raise StarletteHTTPException(404, "Такого файла нет.")
        return FileResponse(файл, filename=файл.name)

    @app.get("/api/work-agents/doc/{name}")
    def готовый_документ(name: str):
        файл = documents.ПАПКА_ДОКУМЕНТОВ / Path(name).name
        if not файл.is_file():
            raise StarletteHTTPException(404, "Такого файла нет.")
        return FileResponse(файл, filename=файл.name)

    class ПечатьЗапрос(BaseModel):
        запрос: str = Field(max_length=200)

    @app.post("/api/work-agents/print")
    def печать_путевого(з: ПечатьЗапрос):
        """Найти путевой лист по фамилии/машине и отправить на принтер (то же, что просьба в чате)."""
        найдено = printing.найти(_непустой(з.запрос, "Запрос"))
        if not найдено:
            raise StarletteHTTPException(404, "Подходящих путевых листов не нашлось.")
        if len(найдено) > 1:
            raise StarletteHTTPException(409, "Подходит несколько: " + "; ".join(printing.подпись(п) for п in найдено[:12]))
        printing.отправить_в_фоне(найдено, при_ошибке=work_agents._ошибка_печати)
        return {"файл": printing.подпись(найдено[0])}

    # ---- Архив: контрагенты → договоры → документы ------------------------------------------

    def _архив(действие):
        try:
            return действие()
        except archive.ОшибкаАрхива as ошибка:
            raise StarletteHTTPException(400, str(ошибка))

    class КонтрагентЗапрос(BaseModel):
        название: str = Field("", max_length=200)
        инн: str = Field("", max_length=12)
        кпп: str = Field("", max_length=9)
        адрес: str = Field("", max_length=300)
        телефон: str = Field("", max_length=60)
        email: str = Field("", max_length=120)
        контакт: str = Field("", max_length=200)
        банк: str = Field("", max_length=300)
        заметка: str = Field("", max_length=2000)

    class ФайлПравка(BaseModel):
        имя: str | None = Field(None, max_length=200)
        контрагент_id: int | None = None
        договор_id: int | None = None
        раздел: str | None = Field(None, max_length=60)
        вид: str | None = Field(None, max_length=60)
        номер: str | None = Field(None, max_length=60)
        дата: str | None = Field(None, max_length=10)
        сумма: float | str | None = None
        описание: str | None = Field(None, max_length=300)

    class ДоговорЗапрос(BaseModel):
        контрагент_id: int
        вид: str = Field("договор", max_length=20)
        номер: str = Field("", max_length=60)
        дата: str | None = Field(None, max_length=10)
        сумма: float | None = None
        предмет: str = Field("", max_length=500)

    class ЗакупкаЗапрос(BaseModel):
        статус: str = Field("", max_length=30)

    @app.get("/api/archive/tree")
    def архив_дерево():
        return archive.дерево(база)

    @app.get("/api/archive/contractors/{cid}")
    def архив_контрагент(cid: int):
        к = _архив(lambda: archive.контрагент(база, cid))
        return {"контрагент": к, "файлы": archive.файлы(база, контрагент_id=cid),
                "договоры": [{**д, "комплект": archive.комплект(база, д["id"])}
                             for д in work.список(база, "договоры") + work.список(база, "оферты") if д.get("контрагент_id") == cid]}

    @app.post("/api/archive/contractors", status_code=201)
    def архив_создать_контрагента(з: КонтрагентЗапрос):
        return _архив(lambda: archive.создать_контрагента(база, з.model_dump()))

    @app.put("/api/archive/contractors/{cid}")
    def архив_изменить_контрагента(cid: int, з: КонтрагентЗапрос):
        return _архив(lambda: archive.изменить_контрагента(база, cid, з.model_dump()))

    @app.delete("/api/archive/contractors/{cid}")
    def архив_удалить_контрагента(cid: int):
        _архив(lambda: archive.удалить_контрагента(база, cid))
        return {"удалено": cid}

    @app.post("/api/archive/dogovor", status_code=201)
    def архив_договор(з: ДоговорЗапрос):
        return _архив(lambda: archive.создать_договор(база, з.контрагент_id, з.вид, з.номер, з.дата, з.сумма, з.предмет))

    @app.get("/api/archive/files")
    def архив_файлы(kontragent: int | None = None, dogovor: int | None = None, inbox: bool = False, q: str = Query("", max_length=200)):
        if q.strip():
            return {"файлы": archive.искать(база, q, 40)}
        return {"файлы": archive.файлы(база, kontragent, dogovor, inbox)}

    @app.post("/api/archive/upload", status_code=201)
    async def архив_загрузка(request: Request, name: str = Query("файл", max_length=200), kontragent: int | None = None,
                             dogovor: int | None = None, razdel: str | None = Query(None, max_length=60),
                             rename: bool = True):
        данные = await request.body()
        н = dict(_ии())
        with agents.работа("архивариус", "принял файл в архив", f"«{name}»") as з:
            итог = await run_in_threadpool(lambda: _архив(lambda: archive.принять_файл(
                база, н, name, данные, kontragent, dogovor, razdel, None, rename)))
            з["результат"] = f"{итог['вид']} → {итог['где']}"
            з["польза"] = 2
        return итог

    @app.get("/api/archive/file/{fid}")
    def архив_скачать(fid: int):
        п = _архив(lambda: archive.путь_на_диске(база, fid))
        return FileResponse(п, filename=п.name)

    @app.patch("/api/archive/file/{fid}")
    def архив_править(fid: int, з: ФайлПравка):
        return _архив(lambda: archive.изменить_файл(база, fid, з.model_dump(exclude_unset=True)))

    @app.post("/api/archive/file/{fid}/rename-auto")
    def архив_имя_по_схеме(fid: int):
        return _архив(lambda: archive.переименовать_по_схеме(база, fid))

    @app.delete("/api/archive/file/{fid}")
    def архив_удалить_файл(fid: int):
        _архив(lambda: archive.удалить_файл(база, fid))
        return {"удалено": fid}

    @app.post("/api/archive/sort-inbox")
    def архив_разобрать_входящие():
        с_ = agents.работа("архивариус", "разбираю входящие", "по кнопке")
        with с_ as з:
            n = archive.разобрать_входящие(база, dict(_ии()))
            з["результат"] = f"разложено: {n}"
            з["польза"] = 1 + min(n, 3)
        return {"разложено": n}

    @app.get("/api/archive/procurement/{did}")
    def архив_комплект(did: int):
        return _архив(lambda: archive.комплект(база, did))

    @app.get("/api/archive/procurement/{did}/zip")
    def архив_комплект_zip(did: int):
        from fastapi.responses import Response
        from urllib.parse import quote
        имя, данные = _архив(lambda: archive.комплект_zip(база, did))
        return Response(данные, media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(имя)}"})

    @app.post("/api/archive/procurement/{did}")
    def архив_статус_закупки(did: int, з: ЗакупкаЗапрос):
        return _архив(lambda: archive.задать_закупку(база, did, з.статус))

    @app.post("/api/work-agents/memo", status_code=201)
    def записка_инженера(з: ЗаписокЗапрос):
        return work_agents.написать_записку(база, dict(_ии()), _непустой(з.тема, "Тема записки"),
                                            з.пояснение, з.кому, з.от_кого)

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
            "учёба": soul.учёба(база),
            "рост": soul.путь_роста(база),
            "учёба_агентов": learning.состояние(),
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

    # Функции графа: путь между точками, проверка, предложения связей.
    @app.get("/api/brain/path")
    def мозги_путь(а: str = Query("", alias="a"), б: str = Query("", alias="b")):
        return graph_tools.путь(база, а, б)

    @app.get("/api/brain/audit")
    def мозги_проверка():
        return graph_tools.аудит(база)

    @app.get("/api/brain/suggest")
    def мозги_предложения():
        return graph_tools.предложить_связи(база, _ии())

    class ДействиеГрафа(BaseModel):
        действие: str
        а: str = ""
        б: str = ""
        отношение: str = "связано с"

    @app.post("/api/brain/apply")
    def мозги_применить(д: ДействиеГрафа):
        try:
            return graph_tools.применить(база, д.действие, д.а, д.б, д.отношение)
        except ValueError as ошибка:
            return JSONResponse({"ошибка": str(ошибка)}, status_code=400)

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

    work_agents.запустить_фоновое_развитие(база, _ии)
    senses.запустить_уши(база, _ии)
    learning.запустить(база, _ии)
    evolve.запустить(_ии)
    memory_plus.запустить(база, _ии)
    soul.запустить_фоновое_развитие(
        база, _ии, lambda: последняя_активность[0]
    )
    return app
