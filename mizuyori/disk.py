"""Диск: резервные копии (база + файлы), уход за корзиной, проверка целостности."""

import logging
import sqlite3
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

from . import archive
from .paths import ПАПКА_ДАННЫХ

журнал = logging.getLogger("mizuyori.диск")

ПАПКА_КОПИЙ = ПАПКА_ДАННЫХ / "копии"
ХРАНИТЬ_КОПИЙ = 7
ПЕРИОД_СУТКИ = 24 * 3600
_замок = threading.Lock()


def копии() -> list[dict]:
    if not ПАПКА_КОПИЙ.is_dir():
        return []
    список = sorted(ПАПКА_КОПИЙ.glob("диск_*.zip"), key=lambda п: п.stat().st_mtime, reverse=True)
    return [{"имя": п.name, "размер": п.stat().st_size,
             "создано": datetime.fromtimestamp(п.stat().st_mtime).strftime("%Y-%m-%d %H:%M")} for п in список]


def путь_копии(имя: str) -> Path:
    п = ПАПКА_КОПИЙ / Path(имя).name
    if not п.is_file() or not п.name.startswith("диск_"):
        raise archive.ОшибкаАрхива("Такой копии нет.")
    return п


def резервная_копия(база) -> dict:
    """Один zip: снимок базы (целостный, даже если база в работе) и все файлы Диска вместе с версиями."""
    with _замок:
        ПАПКА_КОПИЙ.mkdir(parents=True, exist_ok=True)
        имя = f"диск_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        цель = ПАПКА_КОПИЙ / имя
        with tempfile.TemporaryDirectory() as врем:
            снимок = Path(врем) / "база.sqlite"
            источник = sqlite3.connect(база.файл, timeout=30)
            приёмник = sqlite3.connect(снимок)
            try:
                источник.backup(приёмник)
            finally:
                приёмник.close()
                источник.close()
            файлов = 0
            with zipfile.ZipFile(str(цель) + ".part", "w", zipfile.ZIP_DEFLATED) as з:
                з.write(снимок, "база.sqlite")
                if archive.ПАПКА.is_dir():
                    for п in archive.ПАПКА.rglob("*"):
                        if п.is_file():
                            з.write(п, "архив/" + п.relative_to(archive.ПАПКА).as_posix())
                            файлов += 1
        Path(str(цель) + ".part").replace(цель)
        for старая in копии()[ХРАНИТЬ_КОПИЙ:]:
            (ПАПКА_КОПИЙ / старая["имя"]).unlink(missing_ok=True)
        журнал.info("Резервная копия Диска: %s (%d файлов)", имя, файлов)
        return {"имя": имя, "размер": цель.stat().st_size, "файлов": файлов}


def нужна_копия() -> bool:
    список = копии()
    if not список:
        return True
    п = ПАПКА_КОПИЙ / список[0]["имя"]
    return time.time() - п.stat().st_mtime > ПЕРИОД_СУТКИ


def уход(база) -> dict:
    """Раз в сутки: копия, если давно не было; корзина старше срока убирается. Безопасно звать часто."""
    итог = {"копия": None, "убрано_из_корзины": 0}
    try:
        итог["убрано_из_корзины"] = archive.очистить_корзину(база)
        if нужна_копия():
            итог["копия"] = резервная_копия(база)["имя"]
    except Exception:
        журнал.exception("Уход за Диском не удался")
    return итог


def уход_в_фоне(база) -> None:
    if not нужна_копия() and not archive.корзина(база):
        return
    threading.Thread(target=уход, args=(база,), daemon=True).start()


def проверка(база) -> dict:
    """Файлы без записи и записи без файла."""
    пропали, лишние = [], []
    известные = set()
    with база.соединение() as связь:
        строки = [dict(р) for р in связь.execute("SELECT id, имя, путь FROM раб_файлы")]
        версии = [р[0] for р in связь.execute("SELECT путь FROM раб_версии")]
    for р in строки:
        известные.add(р["путь"])
        if not (archive.ПАПКА / р["путь"]).is_file():
            пропали.append({"id": р["id"], "имя": р["имя"]})
    известные.update(версии)
    if archive.ПАПКА.is_dir():
        for п in archive.ПАПКА.rglob("*"):
            if п.is_file() and п.relative_to(archive.ПАПКА).as_posix() not in известные:
                лишние.append(п.relative_to(archive.ПАПКА).as_posix())
    return {"пропали_с_диска": пропали, "лишние_файлы": лишние[:50]}
