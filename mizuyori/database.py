"""База данных SQLite в data/mizuyori.db."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .work import МИГРАЦИЯ as МИГРАЦИЯ_РАБОТЫ, МИГРАЦИЯ_ПУТЕВЫХ

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
    # 3: память ИИ и смысловые вектора
    """
    CREATE TABLE память (
        id       INTEGER PRIMARY KEY,
        факт     TEXT NOT NULL,
        источник INTEGER,            -- id сообщения, из которого запомнено
        создано  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE вектора (
        ключ      TEXT PRIMARY KEY,  -- «з12» задача, «н3» заметка, «п5» факт памяти
        модель    TEXT NOT NULL,
        отпечаток TEXT NOT NULL,     -- чтобы пересчитать, если текст изменился
        вектор    BLOB NOT NULL      -- float32
    );
    """,
    # 4: категории и важность фактов, сводка чата, рабочая память
    """
    ALTER TABLE память ADD COLUMN категория TEXT NOT NULL DEFAULT 'другое';
    ALTER TABLE память ADD COLUMN важность INTEGER NOT NULL DEFAULT 3;
    ALTER TABLE память ADD COLUMN изменено TEXT;
    CREATE TABLE сводки (
        id           INTEGER PRIMARY KEY,
        до_сообщения INTEGER NOT NULL,   -- сводка охватывает сообщения с id ≤ этого
        текст        TEXT NOT NULL,
        создано      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE состояние (
        ключ     TEXT PRIMARY KEY,
        значение TEXT NOT NULL
    );
    """,
    # 5: понимание — сущности (люди, места, цели…), связи между ними, смысл фактов, цели у задач
    """
    CREATE TABLE сущности (
        id           INTEGER PRIMARY KEY,
        имя          TEXT NOT NULL,
        ключ         TEXT NOT NULL UNIQUE,         -- имя в нижнем регистре, для поиска
        тип          TEXT NOT NULL DEFAULT 'другое',
        описание     TEXT NOT NULL DEFAULT '',
        другие_имена TEXT NOT NULL DEFAULT '[]',   -- JSON: «мама», «мамуля»…
        причина      TEXT NOT NULL DEFAULT '',     -- для целей: почему это важно
        статус       TEXT NOT NULL DEFAULT '',     -- для целей: активна | достигнута | отменена
        создано      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        изменено     TEXT
    );
    CREATE TABLE отношения (
        id        INTEGER PRIMARY KEY,
        от_id     INTEGER NOT NULL REFERENCES сущности(id) ON DELETE CASCADE,
        отношение TEXT NOT NULL,                   -- «любит», «для», «потому что», «чтобы»…
        к_id      INTEGER NOT NULL REFERENCES сущности(id) ON DELETE CASCADE,
        создано   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (от_id, отношение, к_id)
    );
    CREATE TABLE факт_сущность (
        факт_id     INTEGER NOT NULL REFERENCES память(id) ON DELETE CASCADE,
        сущность_id INTEGER NOT NULL REFERENCES сущности(id) ON DELETE CASCADE,
        PRIMARY KEY (факт_id, сущность_id)
    );
    ALTER TABLE память ADD COLUMN смысл TEXT NOT NULL DEFAULT '{}';  -- JSON: кто, что, для_кого, зачем, почему, когда
    ALTER TABLE задачи ADD COLUMN цель_id INTEGER REFERENCES сущности(id) ON DELETE SET NULL;
    """,
    # 6: внутренняя мысль ИИ перед ответом
    """
    ALTER TABLE сообщения ADD COLUMN мысль TEXT NOT NULL DEFAULT '';
    """,
    # 7: агенты — история решений, своя память (правила, приёмы, ошибки), общая доска записок
    """
    CREATE TABLE агент_история (
        id        INTEGER PRIMARY KEY,
        агент     TEXT NOT NULL,
        действие  TEXT NOT NULL,
        почему    TEXT NOT NULL DEFAULT '',
        результат TEXT NOT NULL DEFAULT '',
        успех     INTEGER NOT NULL DEFAULT 1,
        польза    INTEGER NOT NULL DEFAULT 0,
        секунд    REAL NOT NULL DEFAULT 0,
        создано   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX агент_история_агент ON агент_история(агент, id);
    CREATE TABLE агент_заметки (
        id       INTEGER PRIMARY KEY,
        агент    TEXT NOT NULL,
        вид      TEXT NOT NULL CHECK (вид IN ('правило', 'приём', 'ошибка')),
        текст    TEXT NOT NULL,
        источник TEXT NOT NULL DEFAULT 'сам',      -- сам | вы
        счёт     INTEGER NOT NULL DEFAULT 1,       -- сколько раз повторилось (для ошибок)
        создано  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        изменено TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE доска (
        id        INTEGER PRIMARY KEY,
        от        TEXT NOT NULL,                   -- ключ агента или «вы»
        кому      TEXT NOT NULL,                   -- ключ агента или «все»
        текст     TEXT NOT NULL,
        прочитано INTEGER NOT NULL DEFAULT 0,
        создано   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    """,
    # 8: «Работа» — сотрудники, автомобили, топливные карты, ГСМ, табель, служебные записки, договоры
    МИГРАЦИЯ_РАБОТЫ,
    # 9: «Работа» → ГСМ → расчёт по путевым листам (км и остатки на начало и конец месяца)
    МИГРАЦИЯ_ПУТЕВЫХ,
]

ТИПЫ_СУЩНОСТЕЙ = ["человек", "питомец", "место", "организация", "проект", "цель", "событие", "вещь", "другое"]
ПОЛЯ_СМЫСЛА = ["кто", "что", "для_кого", "зачем", "почему", "когда"]


def ключ_имени(имя: str) -> str:
    return " ".join(имя.casefold().replace("ё", "е").split())


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
                "SELECT * FROM (SELECT id, роль, текст, мысль, создано FROM сообщения "
                "ORDER BY id DESC LIMIT ?) ORDER BY id", (сколько,)).fetchall()
        return [dict(с) for с in строки]

    def добавить_сообщение(self, роль: str, текст: str, мысль: str = "") -> dict:
        with self.соединение() as связь:
            курсор = связь.execute("INSERT INTO сообщения (роль, текст, мысль) VALUES (?, ?, ?)", (роль, текст, мысль))
            строка = связь.execute("SELECT id, роль, текст, мысль, создано FROM сообщения WHERE id = ?",
                                   (курсор.lastrowid,)).fetchone()
        return dict(строка)

    def очистить_чат(self) -> None:
        with self.соединение() as связь:
            связь.execute("DELETE FROM сообщения")

    # ---- Задачи ---------------------------------------------------------

    _ПОЛЯ_ЗАДАЧИ = "id, текст, готово, срок, список_id, цель_id, создано"

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
        разрешённые = {"текст", "готово", "срок", "список_id", "цель_id"}
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

    # ---- Память ИИ ------------------------------------------------------

    _ПОЛЯ_ФАКТА = "id, факт, источник, категория, важность, смысл, создано, изменено"

    @staticmethod
    def _факт(строка) -> dict:
        ф = dict(строка)
        try:
            ф["смысл"] = json.loads(ф.get("смысл") or "{}")
        except ValueError:
            ф["смысл"] = {}
        return ф

    def память(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute(f"SELECT {self._ПОЛЯ_ФАКТА} FROM память ORDER BY важность DESC, id").fetchall()
            пары = связь.execute("SELECT факт_id, сущность_id FROM факт_сущность").fetchall()
        сущности: dict[int, list[int]] = {}
        for п in пары:
            сущности.setdefault(п[0], []).append(п[1])
        итог = []
        for с in строки:
            ф = self._факт(с)
            ф["сущности"] = сущности.get(ф["id"], [])
            итог.append(ф)
        return итог

    def факт(self, номер: int) -> dict | None:
        with self.соединение() as связь:
            строка = связь.execute(f"SELECT {self._ПОЛЯ_ФАКТА} FROM память WHERE id = ?", (номер,)).fetchone()
        return self._факт(строка) if строка else None

    def запомнить(self, факт: str, источник: int | None = None,
                  категория: str = "другое", важность: int = 3, смысл: dict | None = None) -> dict | None:
        """Новый факт. Точный повтор (без учёта регистра) не добавляется."""
        ключ = ключ_имени(факт)
        with self.соединение() as связь:
            for (текст,) in связь.execute("SELECT факт FROM память").fetchall():
                if ключ_имени(текст) == ключ:
                    return None
            номер = связь.execute(
                "INSERT INTO память (факт, источник, категория, важность, смысл) VALUES (?, ?, ?, ?, ?)",
                (факт, источник, категория, важность, json.dumps(смысл or {}, ensure_ascii=False))).lastrowid
        return self.факт(номер)

    def изменить_факт(self, номер: int, поля: dict) -> dict | None:
        if "смысл" in поля:
            поля = {**поля, "смысл": json.dumps(поля["смысл"] or {}, ensure_ascii=False)}
        поля = {к: з for к, з in поля.items() if к in {"факт", "категория", "важность", "источник", "смысл"}}
        if поля:
            набор = ", ".join(f"{к} = ?" for к in поля)
            with self.соединение() as связь:
                связь.execute(f"UPDATE память SET {набор}, изменено = datetime('now', 'localtime') WHERE id = ?",
                              (*поля.values(), номер))
        return self.факт(номер)

    def забыть(self, номер: int) -> bool:
        with self.соединение() as связь:
            связь.execute("DELETE FROM вектора WHERE ключ = ?", (f"п{номер}",))
            return связь.execute("DELETE FROM память WHERE id = ?", (номер,)).rowcount > 0

    def забыть_всё(self) -> None:
        with self.соединение() as связь:
            связь.execute("DELETE FROM память")
            связь.execute("DELETE FROM вектора WHERE ключ LIKE 'п%'")

    # ---- Сводка чата и рабочая память ------------------------------------

    def сводка(self) -> dict | None:
        with self.соединение() as связь:
            строка = связь.execute("SELECT id, до_сообщения, текст, создано FROM сводки ORDER BY id DESC LIMIT 1").fetchone()
        return dict(строка) if строка else None

    def сохранить_сводку(self, до_сообщения: int, текст: str) -> None:
        with self.соединение() as связь:
            связь.execute("INSERT INTO сводки (до_сообщения, текст) VALUES (?, ?)", (до_сообщения, текст))
            # храним только несколько последних
            связь.execute("DELETE FROM сводки WHERE id NOT IN (SELECT id FROM сводки ORDER BY id DESC LIMIT 5)")

    def сообщения_между(self, после: int, до: int) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute("SELECT id, роль, текст, создано FROM сообщения WHERE id > ? AND id <= ? ORDER BY id",
                                   (после, до)).fetchall()
        return [dict(с) for с in строки]

    def прочитать(self, ключ: str, по_умолчанию=None):
        with self.соединение() as связь:
            строка = связь.execute("SELECT значение FROM состояние WHERE ключ = ?", (ключ,)).fetchone()
        return json.loads(строка[0]) if строка else по_умолчанию

    def записать(self, ключ: str, значение) -> None:
        with self.соединение() as связь:
            связь.execute("INSERT OR REPLACE INTO состояние (ключ, значение) VALUES (?, ?)",
                          (ключ, json.dumps(значение, ensure_ascii=False)))

    def очистить_разговор(self) -> None:
        """Чат очищен — сводка и рабочая память больше не нужны."""
        with self.соединение() as связь:
            связь.execute("DELETE FROM сводки")
            связь.execute("DELETE FROM состояние WHERE ключ = 'рабочая'")

    # ---- Смысловые вектора ----------------------------------------------

    def вектора(self, модель: str) -> dict[str, tuple[str, bytes]]:
        with self.соединение() as связь:
            строки = связь.execute("SELECT ключ, отпечаток, вектор FROM вектора WHERE модель = ?", (модель,)).fetchall()
        return {с["ключ"]: (с["отпечаток"], с["вектор"]) for с in строки}

    def сохранить_вектора(self, модель: str, записи: list[tuple[str, str, bytes]]) -> None:
        with self.соединение() as связь:
            связь.executemany(
                "INSERT OR REPLACE INTO вектора (ключ, модель, отпечаток, вектор) VALUES (?, ?, ?, ?)",
                [(ключ, модель, отпечаток, вектор) for ключ, отпечаток, вектор in записи])

    def убрать_лишние_вектора(self, нужные: set[str]) -> None:
        with self.соединение() as связь:
            for (ключ,) in связь.execute("SELECT ключ FROM вектора").fetchall():
                if ключ not in нужные:
                    связь.execute("DELETE FROM вектора WHERE ключ = ?", (ключ,))

    # ---- Понимание: сущности и связи --------------------------------------

    _ПОЛЯ_СУЩНОСТИ = "id, имя, тип, описание, другие_имена, причина, статус, создано, изменено"

    @staticmethod
    def _сущность(строка) -> dict:
        с = dict(строка)
        try:
            с["другие_имена"] = json.loads(с.get("другие_имена") or "[]")
        except ValueError:
            с["другие_имена"] = []
        return с

    def сущности(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute(f"SELECT {self._ПОЛЯ_СУЩНОСТИ} FROM сущности ORDER BY тип, имя").fetchall()
        return [self._сущность(с) for с in строки]

    def сущность(self, номер: int) -> dict | None:
        with self.соединение() as связь:
            строка = связь.execute(f"SELECT {self._ПОЛЯ_СУЩНОСТИ} FROM сущности WHERE id = ?", (номер,)).fetchone()
        return self._сущность(строка) if строка else None

    def найти_сущность(self, имя: str) -> dict | None:
        """По имени или другому имени, без учёта регистра и «ё»."""
        ключ = ключ_имени(имя)
        if not ключ:
            return None
        for с in self.сущности():
            if ключ_имени(с["имя"]) == ключ or any(ключ_имени(д) == ключ for д in с["другие_имена"]):
                return с
        return None

    def сущность_или_новая(self, имя: str, тип: str = "другое", описание: str = "",
                           другие_имена: list[str] | None = None) -> dict:
        """Найти по имени или создать. Уточняет тип, описание и другие имена, если их не было."""
        имя = " ".join(имя.split())[:80]
        тип = тип if тип in ТИПЫ_СУЩНОСТЕЙ else "другое"
        другие = [" ".join(д.split())[:80] for д in (другие_имена or []) if isinstance(д, str) and д.strip()]
        есть = self.найти_сущность(имя) or next((self.найти_сущность(д) for д in другие if self.найти_сущность(д)), None)
        if есть:
            поля = {}
            if есть["тип"] == "другое" and тип != "другое":
                поля["тип"] = тип
            if описание and not есть["описание"]:
                поля["описание"] = описание[:300]
            новые = [д for д in другие + ([имя] if ключ_имени(имя) != ключ_имени(есть["имя"]) else [])
                     if ключ_имени(д) not in {ключ_имени(х) for х in есть["другие_имена"] + [есть["имя"]]}]
            if новые:
                поля["другие_имена"] = есть["другие_имена"] + новые
            return self.изменить_сущность(есть["id"], поля) if поля else есть
        with self.соединение() as связь:
            номер = связь.execute(
                "INSERT INTO сущности (имя, ключ, тип, описание, другие_имена, статус) VALUES (?, ?, ?, ?, ?, ?)",
                (имя, ключ_имени(имя), тип, описание[:300], json.dumps(другие, ensure_ascii=False),
                 "активна" if тип == "цель" else "")).lastrowid
        return self.сущность(номер)

    def изменить_сущность(self, номер: int, поля: dict) -> dict | None:
        поля = {к: з for к, з in поля.items() if к in {"имя", "тип", "описание", "другие_имена", "причина", "статус"}}
        if "другие_имена" in поля:
            поля["другие_имена"] = json.dumps(поля["другие_имена"], ensure_ascii=False)
        if "имя" in поля:
            поля["ключ"] = ключ_имени(поля["имя"])
        if поля:
            набор = ", ".join(f"{к} = ?" for к in поля)
            with self.соединение() as связь:
                связь.execute(f"UPDATE сущности SET {набор}, изменено = datetime('now', 'localtime') WHERE id = ?",
                              (*поля.values(), номер))
        return self.сущность(номер)

    def удалить_сущность(self, номер: int) -> bool:
        with self.соединение() as связь:
            связь.execute("DELETE FROM вектора WHERE ключ = ?", (f"е{номер}",))
            return связь.execute("DELETE FROM сущности WHERE id = ?", (номер,)).rowcount > 0

    def отношения(self) -> list[dict]:
        with self.соединение() as связь:
            строки = связь.execute("SELECT id, от_id, отношение, к_id, создано FROM отношения ORDER BY id").fetchall()
        return [dict(с) for с in строки]

    def связать(self, от_id: int, отношение: str, к_id: int) -> None:
        if от_id == к_id:
            return
        with self.соединение() as связь:
            связь.execute("INSERT OR IGNORE INTO отношения (от_id, отношение, к_id) VALUES (?, ?, ?)",
                          (от_id, " ".join(отношение.split())[:40], к_id))

    def удалить_отношение(self, номер: int) -> bool:
        with self.соединение() as связь:
            return связь.execute("DELETE FROM отношения WHERE id = ?", (номер,)).rowcount > 0

    def привязать_факт(self, факт_id: int, сущность_id: int) -> None:
        with self.соединение() as связь:
            связь.execute("INSERT OR IGNORE INTO факт_сущность (факт_id, сущность_id) VALUES (?, ?)", (факт_id, сущность_id))

    def цели(self) -> list[dict]:
        return [с for с in self.сущности() if с["тип"] == "цель"]

    def найти_сообщения(self, слова: list[str], сколько: int = 5) -> list[dict]:
        """Последние сообщения, где встречается любое из слов (без учёта регистра — в Python)."""
        ключи = [ключ_имени(с) for с in слова if с.strip()]
        if not ключи:
            return []
        итог = []
        for с in reversed(self.сообщения(1000)):
            текст = ключ_имени(с["текст"])
            if any(к in текст for к in ключи):
                итог.append(с)
                if len(итог) >= сколько:
                    break
        return итог
