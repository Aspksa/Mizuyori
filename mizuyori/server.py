"""Веб-сервер: страница и API."""

import logging
import platform

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import ТЕМЫ, сохранить_настройки
from .database import База
from .paths import ПАПКА_СТАТИКИ, ФАЙЛ_НАСТРОЕК

журнал = logging.getLogger("mizuyori.сервер")


class ИзменениеНастроек(BaseModel):
    тема: str | None = None


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
        html = html.replace("{{тема}}", настройки["тема"]).replace("{{имя}}", настройки["имя"])
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
            "тема": настройки["тема"],
            "темы": [{"ключ": ключ, "название": название} for ключ, название in ТЕМЫ.items()],
        }

    @app.put("/api/settings")
    def изменить_настройки(изменение: ИзменениеНастроек):
        if изменение.тема is not None:
            if изменение.тема not in ТЕМЫ:
                raise StarletteHTTPException(400, "Такой темы нет.")
            if изменение.тема != настройки["тема"]:
                настройки["тема"] = изменение.тема
                сохранить_настройки(ФАЙЛ_НАСТРОЕК, настройки)
                журнал.info("Тема сайта: %s", ТЕМЫ[изменение.тема])
        return получить_настройки()

    return app
