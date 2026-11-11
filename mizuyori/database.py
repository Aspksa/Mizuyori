"""База данных SQLite в data/mizuyori.db."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

журнал = logging.getLogger("mizuyori.база")

# Каждое изменение структуры базы — новый шаг. Уже применённые шаги
# не повторяются: номер последнего хранится в PRAGMA user_version.
МИГРАЦИИ: list[str] = [
    # 1: чат, задачи, заметки
    """
    CREATE TABLE сообщения (
        id      INTEGER PRIMARY KEY,
        роль    TEXT NOT NULL CHECK (роль IN ('пользователь', 'ии')),
        текст   TEXT NOT NULL,
        создано TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE задачи (
        id      INTEGER PRIMARY KEY,
        текст   TEXT NOT NULL,
        готово  INTEGER NOT NULL DEFAULT 0,
        создано TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE заметки (
        id       INTEGER PRIMARY KEY,
        текст    TEXT NOT NULL,
        создано  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        изменено TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
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

    # ---- Чат ------------------------------------------------------------

    def сообщения(self, сколько: int = 200) -> list[dict]:
        """Последние сообщения чата, от старых к новым."""
        with self.соединение() as связь:
            строки = связь.execute(
                "SELECT * FROM (SELECT id, роль, текст, создано FROM сообщения "
                "ORDER BY id DESC LIMIT ?) ORDER BY id", (сколько,)).fetchall()
        return [dict(с) for с in строки]

    def добавить_сообщение(self, роль: str, текст: str) -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO сообщения (роль, текст) VALUES (?, ?)", (роль, текст))
            строка = связь.execute("SELECT id, роль, текст, создано FROM сообщения WHERE id = ?",
                                   (курсор.lastrowid,)).fetchone()
        return dict(строка)

    def очистить_чат(self) -> None:
        with self.соединение() as связь:
            связь.execute("DELETE FROM сообщения")

    # ---- Задачи ---------------------------------------------------------

    @staticmethod
    def _задача(строка) -> dict:
        задача = dict(строка)
        задача["готово"] = bool(задача["готово"])
        return задача

    def задачи(self) -> list[dict]:
        """Сначала невыполненные (новые сверху), потом выполненные."""
        with self.соединение() as связь:
            строки = связь.execute(
                "SELECT id, текст, готово, создано FROM задачи ORDER BY готово, id DESC").fetchall()
        return [self._задача(с) for с in строки]

    def добавить_задачу(self, текст: str) -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO задачи (текст) VALUES (?)", (текст,))
            строка = связь.execute("SELECT id, текст, готово, создано FROM задачи WHERE id = ?",
                                   (курсор.lastrowid,)).fetchone()
        return self._задача(строка)

    def изменить_задачу(self, номер: int, текст: str | None = None, готово: bool | None = None) -> dict | None:
        with self.соединение() as связь:
            if текст is not None:
                связь.execute("UPDATE задачи SET текст = ? WHERE id = ?", (текст, номер))
            if готово is not None:
                связь.execute("UPDATE задачи SET готово = ? WHERE id = ?", (int(готово), номер))
            строка = связь.execute("SELECT id, текст, готово, создано FROM задачи WHERE id = ?",
                                   (номер,)).fetchone()
        return self._задача(строка) if строка else None

    def удалить_задачу(self, номер: int) -> bool:
        with self.соединение() as связь:
            return связь.execute("DELETE FROM задачи WHERE id = ?", (номер,)).rowcount > 0

    # ---- Заметки --------------------------------------------------------

    def заметки(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute(
                "SELECT id, текст, создано, изменено FROM заметки ORDER BY изменено DESC, id DESC").fetchall()
        return [dict(с) for с in строки]

    def добавить_заметку(self, текст: str) -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO заметки (текст) VALUES (?)", (текст,))
            строка = связь.execute("SELECT id, текст, создано, изменено FROM заметки WHERE id = ?",
                                   (курсор.lastrowid,)).fetchone()
        return dict(строка)

    def изменить_заметку(self, номер: int, текст: str) -> dict | None:
        with self.соединение() as связь:
            связь.execute("UPDATE заметки SET текст = ?, изменено = datetime('now', 'localtime') "
                          "WHERE id = ?", (текст, номер))
            строка = связь.execute("SELECT id, текст, создано, изменено FROM заметки WHERE id = ?",
                                   (номер,)).fetchone()
        return dict(строка) if строка else None

    def удалить_заметку(self, номер: int) -> bool:
        with self.соединение() as связь:
            return связь.execute("DELETE FROM заметки WHERE id = ?", (номер,)).rowcount > 0
