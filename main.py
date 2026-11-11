"""Mizuyori — точка входа. Запускается из Mizuyori.bat."""

import logging
import sys
import threading
import time
import webbrowser

# Русский в консоли Windows: вывод в UTF-8 независимо от кодовой страницы
for поток in (sys.stdout, sys.stderr):
    try:
        поток.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from mizuyori import __version__
from mizuyori.logs import настроить_логи
from mizuyori.paths import ФАЙЛ_БАЗЫ, ФАЙЛ_НАСТРОЕК, ПАПКА_ЛОГОВ

журнал = logging.getLogger("mizuyori")


def адрес_в_сети() -> str | None:
    """IP этого компьютера в локальной сети (для входа с телефона)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # пакет не отправляется, только выбор интерфейса
            return s.getsockname()[0]
    except OSError:
        return None


def открыть_браузер_когда_готов(порт: int) -> None:
    """Ждёт, пока сервер начнёт отвечать, и открывает браузер."""
    from mizuyori.ports import порт_занят

    def ждать():
        for _ in range(100):  # до 10 секунд
            if порт_занят(порт):
                webbrowser.open(f"http://127.0.0.1:{порт}/")
                return
            time.sleep(0.1)
        журнал.warning("Сервер долго не отвечает, браузер не открыт.")

    threading.Thread(target=ждать, daemon=True).start()


def main() -> int:
    файл_журнала = настроить_логи(ПАПКА_ЛОГОВ)
    журнал.info("Запуск Mizuyori %s (Python %s)", __version__, sys.version.split()[0])

    try:
        import uvicorn

        from mizuyori.config import загрузить_настройки
        from mizuyori.database import База
        from mizuyori.ports import найти_свободный_порт
        from mizuyori.server import создать_приложение

        настройки = загрузить_настройки(ФАЙЛ_НАСТРОЕК)
        база = База(ФАЙЛ_БАЗЫ)
        база.подготовить()

        хост = "0.0.0.0" if настройки["доступ_из_сети"] else "127.0.0.1"
        порт = найти_свободный_порт(настройки["порт"])
        приложение = создать_приложение(настройки, база, порт)
    except Exception:
        журнал.exception("Не удалось запустить Mizuyori. Журнал: %s", файл_журнала)
        return 1

    print()
    журнал.info("Mizuyori работает: http://127.0.0.1:%s/", порт)
    if настройки["доступ_из_сети"]:
        ip = адрес_в_сети()
        if ip:
            журнал.info("С телефона в той же сети: http://%s:%s/", ip, порт)
    журнал.info("Чтобы остановить — закройте это окно или нажмите Ctrl+C.")
    print()

    if настройки["открывать_браузер"]:
        открыть_браузер_когда_готов(порт)

    try:
        uvicorn.run(
            приложение,
            host=хост,
            port=порт,
            log_config=None,   # журнал настроен выше, на русском
            log_level="warning",
            access_log=False,
        )
    except KeyboardInterrupt:
        pass
    except Exception:
        журнал.exception("Сервер остановился с ошибкой. Журнал: %s", файл_журнала)
        return 1

    журнал.info("Mizuyori остановлен.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
