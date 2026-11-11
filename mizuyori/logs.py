"""Журнал работы: пишет в консоль и в logs/mizuyori.log."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

РУССКИЕ_УРОВНИ = {
    logging.DEBUG: "ОТЛАДКА",
    logging.INFO: "ИНФО",
    logging.WARNING: "ВНИМАНИЕ",
    logging.ERROR: "ОШИБКА",
    logging.CRITICAL: "КРИТИЧНО",
}


def настроить_логи(папка: Path) -> Path:
    """Включает журнал. Возвращает путь к файлу журнала."""
    папка.mkdir(parents=True, exist_ok=True)
    файл = папка / "mizuyori.log"

    for уровень, название in РУССКИЕ_УРОВНИ.items():
        logging.addLevelName(уровень, название)

    корень = logging.getLogger()
    корень.setLevel(logging.INFO)
    корень.handlers.clear()

    # В файл — подробно, до 1 МБ, хранятся 3 старых файла
    в_файл = RotatingFileHandler(файл, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    в_файл.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
    корень.addHandler(в_файл)

    # В консоль — коротко
    в_консоль = logging.StreamHandler(sys.stdout)
    в_консоль.setFormatter(logging.Formatter("[Mizuyori] %(message)s"))
    корень.addHandler(в_консоль)

    # Любая непойманная ошибка тоже попадает в журнал
    def записать_ошибку(тип, значение, трассировка):
        if issubclass(тип, KeyboardInterrupt):
            sys.__excepthook__(тип, значение, трассировка)
            return
        logging.getLogger("mizuyori").critical(
            "Непредвиденная ошибка", exc_info=(тип, значение, трассировка))

    sys.excepthook = записать_ошибку
    return файл
