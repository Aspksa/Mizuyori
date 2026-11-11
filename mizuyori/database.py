"""База данных SQLite в data/mizuyori.db."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

журнал = logging.getLogger("mizuyori.база")

# Каждое изменение структуры базы — новый шаг. Уже применённые шаги
# не повторяются: номер последнего хранится в PRAGMA user_version.
МИГРАЦИИ = [
    # 1: записи
    """
    CREATE TABLE записи (
        id      INTEGER PRIMARY KEY,
        текст   TEXT NOT NULL,
        создано TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    """,
]


class База:
    def __init__(self, файл: Path):
        self.файл = файл

    @contextmanager
    def соединение(self):
        """Отдельное соединение на каждый запрос: так безопасно для нескольких потоков."""
        связь = sqlite3.connect(self.файл, timeout=10)
        связь.row_factory = sqlite3.Row
        связь.execute("PRAGMA foreign_keys = ON")
        try:
            yield связь
            связь.commit()
        except Exception:
            связь.rollback()
            raise
        finally:
            связь.close()

    def подготовить(self) -> None:
        """Создаёт файл базы и применяет новые миграции."""
        self.файл.parent.mkdir(parents=True, exist_ok=True)
        with self.соединение() as связь:
            связь.execute("PRAGMA journal_mode = WAL")
            версия = связь.execute("PRAGMA user_version").fetchone()[0]
            for номер, sql in enumerate(МИГРАЦИИ[версия:], start=версия + 1):
                журнал.info("Обновляю базу до версии %s", номер)
                связь.executescript(sql)
                связь.execute(f"PRAGMA user_version = {номер}")

    # ---- Записи ---------------------------------------------------------

    def все_записи(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute("SELECT id, текст, создано FROM записи ORDER BY id DESC").fetchall()
        return [dict(строка) for строка in строки]

    def добавить_запись(self, текст: str) -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO записи (текст) VALUES (?)", (текст,))
            строка = связь.execute("SELECT id, текст, создано FROM записи WHERE id = ?",
                                   (курсор.lastrowid,)).fetchone()
        return dict(строка)

    def удалить_запись(self, номер: int) -> bool:
        with self.соединение() as связь:
            курсор = связь.execute("DELETE FROM записи WHERE id = ?", (номер,))
        return курсор.rowcount > 0
