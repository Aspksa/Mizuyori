"""Веб-сервер: страница и API."""

import logging
import platform

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .database import База
from .paths import ПАПКА_СТАТИКИ

журнал = logging.getLogger("mizuyori.сервер")


class НоваяЗапись(BaseModel):
    текст: str = Field(min_length=1, max_length=5000)


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
        return FileResponse(ПАПКА_СТАТИКИ / "index.html")

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

    @app.get("/api/notes")
    def список_записей():
        return база.все_записи()

    @app.post("/api/notes", status_code=201)
    def новая_запись(запись: НоваяЗапись):
        текст = запись.текст.strip()
        if not текст:
            raise HTTPException(400, "Запись не может быть пустой.")
        return база.добавить_запись(текст)

    # Имя параметра в адресе — латиницей: кириллица в шаблоне пути не работает
    @app.delete("/api/notes/{note_id}")
    def удалить_запись(note_id: int):
        if not база.удалить_запись(note_id):
            raise HTTPException(404, "Такой записи нет.")
        return {"удалено": note_id}

    return app
