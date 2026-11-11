"""Пути проекта. Всё хранится рядом с программой, поэтому папку можно переносить."""

from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parent.parent
ПАПКА_ДАННЫХ = КОРЕНЬ / "data"
ПАПКА_ЛОГОВ = КОРЕНЬ / "logs"
ФАЙЛ_НАСТРОЕК = КОРЕНЬ / "config.json"
ФАЙЛ_БАЗЫ = ПАПКА_ДАННЫХ / "mizuyori.db"
ПАПКА_СТАТИКИ = Path(__file__).resolve().parent / "static"
