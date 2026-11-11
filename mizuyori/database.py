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
    # 2: списки задач, срок у задач
    """
    CREATE TABLE списки (
        id       INTEGER PRIMARY KEY,
        название TEXT NOT NULL,
        цвет     TEXT NOT NULL,
        значок   TEXT NOT NULL,
        порядок  INTEGER NOT NULL DEFAULT 0
    );
    INSERT INTO списки (название, цвет, значок, порядок) VALUES
        ('Дом', 'зелёный', '🏠', 1),
        ('Работа', 'синий', '💼', 2),
        ('Покупки', 'оранжевый', '🛒', 3);
    ALTER TABLE задачи ADD COLUMN срок TEXT;
    ALTER TABLE задачи ADD COLUMN список_id INTEGER REFERENCES списки(id) ON DELETE SET NULL;
    CREATE INDEX задачи_срок ON задачи(срок);
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

    _ПОЛЯ_ЗАДАЧИ = "id, текст, готово, срок, список_id, создано"

    @staticmethod
    def _задача(строка) -> dict:
        задача = dict(строка)
        задача["готово"] = bool(задача["готово"])
        return задача

    def задачи(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute(
                f"SELECT {self._ПОЛЯ_ЗАДАЧИ} FROM задачи ORDER BY готово, id DESC").fetchall()
        return [self._задача(с) for с in строки]

    def задача(self, номер: int) -> dict | None:
        with self.соединение() as связь:
            строка = связь.execute(f"SELECT {self._ПОЛЯ_ЗАДАЧИ} FROM задачи WHERE id = ?", (номер,)).fetchone()
        return self._задача(строка) if строка else None

    def добавить_задачу(self, текст: str, срок: str | None = None, список_id: int | None = None) -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO задачи (текст, срок, список_id) VALUES (?, ?, ?)",
                                   (текст, срок, список_id))
            номер = курсор.lastrowid
        return self.задача(номер)

    def изменить_задачу(self, номер: int, поля: dict) -> dict | None:
        """поля — что менять: текст, готово, срок, список_id (None у срока и списка — убрать)."""
        разрешённые = {"текст", "готово", "срок", "список_id"}
        поля = {к: (int(з) if к == "готово" else з) for к, з in поля.items() if к in разрешённые}
        if поля:
            набор = ", ".join(f"{к} = ?" for к in поля)
            with self.соединение() as связь:
                связь.execute(f"UPDATE задачи SET {набор} WHERE id = ?", (*поля.values(), номер))
        return self.задача(номер)

    def удалить_задачу(self, номер: int) -> bool:
        with self.соединение() as связь:
            return связь.execute("DELETE FROM задачи WHERE id = ?", (номер,)).rowcount > 0

    # ---- Списки задач ---------------------------------------------------

    def списки(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute(
                "SELECT id, название, цвет, значок, порядок FROM списки ORDER BY порядок, id").fetchall()
        return [dict(с) for с in строки]

    def список(self, номер: int) -> dict | None:
        with self.соединение() as связь:
            строка = связь.execute("SELECT id, название, цвет, значок, порядок FROM списки WHERE id = ?",
                                   (номер,)).fetchone()
        return dict(строка) if строка else None

    def добавить_список(self, название: str, цвет: str, значок: str) -> dict:
        with self.соединение() as связь:
            порядок = связь.execute("SELECT COALESCE(MAX(порядок), 0) + 1 FROM списки").fetchone()[0]
            курсор = связь.execute("INSERT INTO списки (название, цвет, значок, порядок) VALUES (?, ?, ?, ?)",
                                   (название, цвет, значок, порядок))
            номер = курсор.lastrowid
        return self.список(номер)

    def изменить_список(self, номер: int, поля: dict) -> dict | None:
        поля = {к: з for к, з in поля.items() if к in {"название", "цвет", "значок"}}
        if поля:
            набор = ", ".join(f"{к} = ?" for к in поля)
            with self.соединение() as связь:
                связь.execute(f"UPDATE списки SET {набор} WHERE id = ?", (*поля.values(), номер))
        return self.список(номер)

    def удалить_список(self, номер: int) -> bool:
        """Задачи из списка остаются, просто без списка."""
        with self.соединение() as связь:
            return связь.execute("DELETE FROM списки WHERE id = ?", (номер,)).rowcount > 0

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
