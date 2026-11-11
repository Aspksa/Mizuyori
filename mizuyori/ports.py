"""Поиск свободного порта."""

import logging
import socket

журнал = logging.getLogger("mizuyori.порт")


def порт_занят(порт: int) -> bool:
    # 1) Кто-то уже отвечает на этом порту?
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", порт)) == 0:
            return True
    # 2) Можно ли занять порт самим?
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", порт))
        except OSError:
            return True
    return False


def найти_свободный_порт(начальный: int, попыток: int = 50) -> int:
    for порт in range(начальный, min(начальный + попыток, 65536)):
        if not порт_занят(порт):
            if порт != начальный:
                журнал.warning("Порт %s занят, использую %s.", начальный, порт)
            return порт
    raise RuntimeError(f"Не нашёл свободный порт в диапазоне {начальный}–{начальный + попыток - 1}. "
                       f"Укажите другой «порт» в config.json.")
