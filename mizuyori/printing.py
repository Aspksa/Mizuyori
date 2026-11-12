"""Печать путевых листов: находит шаблон Excel по фамилии/машине и отправляет на принтер двусторонне.

Шаблоны лежат в папке «шаблоны/путевые» (имя файла: «<машина> - <водитель>.xlsx»).
В каждом файле Лист1 — лицевая сторона, Лист2 — оборот, поэтому печатается двусторонне.
Настройки — в config.json, раздел «печать» (принтер, двусторонняя, переворот)."""

import logging
import platform
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from .paths import КОРЕНЬ

журнал = logging.getLogger("mizuyori.печать")

ПАПКА_ШАБЛОНОВ = КОРЕНЬ / "шаблоны" / "путевые"
РАСШИРЕНИЯ = (".xlsx", ".xls")
НАСТРОЙКИ: dict = {"принтер": "", "двусторонняя": True, "переворот": "короткий"}
# слова запроса, которые не нужны для поиска файла
_ЛИШНИЕ = {"распечатай", "распечатать", "напечатай", "напечатать", "печатай", "печать", "отправь", "отправить",
           "на", "принтер", "путевой", "путевые", "путевого", "путевых", "лист", "листы", "листа", "для", "по",
           "двустороннюю", "двусторонняя", "с", "двух", "сторон", "сторонах", "пожалуйста", "и", "в", "а", "у",
           "водителя", "водителю", "машину", "машины", "авто", "автомобиль", "все", "всё", "мне", "нужно", "надо"}
_ПЕЧАТЬ = re.compile(r"(печат|отправ\w* на принтер)")


def _норм(с: str) -> str:
    return re.sub(r"[^0-9a-zа-я]+", " ", с.lower().replace("ё", "е")).strip()


def _основа(слово: str) -> str:
    """Грубая основа слова: «лушкина» и «лушкину» → «лушкин»."""
    if len(слово) > 4:
        слово = re.sub(r"(ого|его|ому|ему|ым|им|ой|ей|ая|яя|ую|юю|ом|ем|ов|ев|а|я|у|ю|е|ы|и|о)$", "", слово)
    return слово


_СИНОНИМЫ = {"хайлюкс": "hilux", "хайлакс": "hilux", "хилюкс": "hilux", "краун": "crown", "тахо": "tahoe",
             "сурф": "surf", "крузер": "cruiser", "круизер": "cruiser", "чейзер": "chaser", "сантафе": "santa",
             "санта": "santa", "исузу": "isuzu", "хино": "hino", "хавал": "haval", "тойота": "toyota",
             "лексус": "lexus", "ленд": "land", "шевроле": "chevrolet", "хендай": "hyundai", "хёндэ": "hyundai"}
_ТРАНСЛИТ = dict(zip("абвгдезиклмнопрстуфхц", "abvgdezIklmnoprstufhc"))
_ТРАНСЛИТ.update({"й": "j", "ж": "zh", "ч": "ch", "ш": "sh", "щ": "sch", "ы": "y", "э": "e", "ю": "yu", "я": "ya", "ъ": "", "ь": ""})
_ТРАНСЛИТ["и"] = "i"


def _латиницей(слово: str) -> str:
    return _СИНОНИМЫ.get(слово) or "".join(_ТРАНСЛИТ.get(б, б) for б in слово)


def это_печать(текст: str) -> bool:
    н = _норм(текст)
    return bool(_ПЕЧАТЬ.search(н)) and "путев" in н


def все_шаблоны() -> list[Path]:
    if not ПАПКА_ШАБЛОНОВ.is_dir():
        return []
    return sorted(п for п in ПАПКА_ШАБЛОНОВ.iterdir()
                  if п.suffix.lower() in РАСШИРЕНИЯ and not п.name.startswith(("~", ".")))


def найти(запрос: str) -> list[Path]:
    """Файлы, в имени которых есть все значимые слова запроса (по основе слова)."""
    слова = [_основа(с) for с in _норм(запрос).split() if с not in _ЛИШНИЕ and len(с) > 1]
    if not слова:
        return []
    итог = []
    for п in все_шаблоны():
        имя = _норм(п.stem)
        части = имя.split()
        if all(any(ч.startswith(с) or с in ч or _латиницей(с) in ч for ч in части) for с in слова):
            итог.append(п)
    return итог


def подпись(п: Path) -> str:
    return п.stem.replace("  ", " ").strip()


# ---- отправка на принтер ----------------------------------------------------

_СКРИПТ_WINDOWS = r"""
param([string]$Path, [string]$Printer, [string]$Duplex)
$ErrorActionPreference = 'Stop'
if ($Printer -eq '') { $Printer = (Get-CimInstance Win32_Printer | Where-Object { $_.Default }).Name }
else { (New-Object -ComObject WScript.Network).SetDefaultPrinter($Printer) }
if ($Duplex -ne '') {
  try { Set-PrintConfiguration -PrinterName $Printer -DuplexingMode $Duplex } catch { Write-Output "duplex-warning: $_" }
}
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
  $wb = $xl.Workbooks.Open($Path, 0, $true)
  $m = [Type]::Missing
  $wb.PrintOut($m, $m, 1, $false)
  $wb.Close($false)
} finally { $xl.Quit() }
"""


def _печатать_windows(файл: Path, принтер: str, режим: str) -> None:
    with tempfile.TemporaryDirectory() as т:
        скрипт = Path(т) / "print.ps1"
        скрипт.write_text(_СКРИПТ_WINDOWS, encoding="utf-8-sig")
        р = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(скрипт),
                            "-Path", str(файл), "-Printer", принтер, "-Duplex", режим],
                           capture_output=True, text=True, timeout=180)
    if р.returncode != 0:
        raise RuntimeError((р.stderr or р.stdout).strip()[:300] or "PowerShell завершился с ошибкой")


def _печатать_unix(файл: Path, принтер: str, режим: str) -> None:
    офис = shutil.which("soffice") or shutil.which("libreoffice")
    if not офис or not shutil.which("lp"):
        raise RuntimeError("Нужны LibreOffice и команда lp (CUPS) для печати на этой системе.")
    with tempfile.TemporaryDirectory() as т:
        subprocess.run([офис, "--headless", "--convert-to", "pdf", "--outdir", т, str(файл)],
                       check=True, capture_output=True, timeout=180)
        pdf = next(Path(т).glob("*.pdf"))
        команда = ["lp"] + (["-d", принтер] if принтер else [])
        if режим:
            команда += ["-o", "sides=" + ("two-sided-short-edge" if режим == "TwoSidedShortEdge" else "two-sided-long-edge")]
        команда.append(str(pdf))
        subprocess.run(команда, check=True, capture_output=True, timeout=60)


def режим_сторон(настройки: dict) -> str:
    if not настройки.get("двусторонняя", True):
        return ""
    return "TwoSidedLongEdge" if настройки.get("переворот") == "длинный" else "TwoSidedShortEdge"


def отправить(файл: Path, настройки: dict | None = None) -> None:
    """Блокирующая отправка одного файла на принтер."""
    н = настройки or НАСТРОЙКИ
    режим = режим_сторон(н)
    принтер = (н.get("принтер") or "").strip()
    журнал.info("Печать «%s» на %s (%s)", файл.name, принтер or "принтер по умолчанию", режим or "односторонняя")
    if platform.system() == "Windows":
        _печатать_windows(файл.resolve(), принтер, режим)
    else:
        _печатать_unix(файл.resolve(), принтер, режим)


def отправить_в_фоне(файлы: list[Path], при_ошибке=None, настройки: dict | None = None) -> None:
    """Печать идёт в отдельном потоке: Excel запускается долго, чат ждать не должен."""
    def работа():
        for ф in файлы:
            try:
                отправить(ф, настройки)
            except Exception as ошибка:
                журнал.exception("Не удалось напечатать %s", ф.name)
                if при_ошибке:
                    при_ошибке(ф, ошибка)
    threading.Thread(target=работа, name="печать", daemon=True).start()
