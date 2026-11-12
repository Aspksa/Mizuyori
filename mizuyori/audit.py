"""Журнал аудита: кто, когда и что подтвердил, отклонил, изменил. Пишется в базу, хранится последние 2000 записей."""

from __future__ import annotations

import logging

журнал = logging.getLogger("mizuyori.аудит")
_база = None


def подключить(база) -> None:
    global _база
    _база = база


def записать(действие: str, объект: str = "", подробности: str = "", кто: str = "вы") -> None:
    """Сбой журнала никогда не ломает основное действие."""
    if not _база:
        return
    try:
        with _база.соединение() as связь:
            связь.execute("INSERT INTO аудит (кто, действие, объект, подробности) VALUES (?, ?, ?, ?)",
                          (кто[:40], действие[:80], " ".join(объект.split())[:160], " ".join(подробности.split())[:400]))
            связь.execute("DELETE FROM аудит WHERE id NOT IN (SELECT id FROM аудит ORDER BY id DESC LIMIT 2000)")
    except Exception:
        журнал.exception("Не удалось записать в журнал аудита")


def список(сколько: int = 100, поиск: str = "") -> list[dict]:
    слово = " ".join(поиск.casefold().split())
    with _база.соединение() as связь:
        строки = связь.execute("SELECT id, кто, действие, объект, подробности, создано FROM аудит ORDER BY id DESC LIMIT 2000").fetchall()
    итог = []
    for с in строки:
        з = dict(с)
        if слово and слово not in f"{з['действие']} {з['объект']} {з['подробности']}".casefold():
            continue
        итог.append(з)
        if len(итог) >= сколько:
            break
    return итог
