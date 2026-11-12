import tempfile
import time
import unittest
from pathlib import Path

from mizuyori import agents, housekeeping, missions, senses, work_agents
from mizuyori.config import проверить_агентов
from mizuyori.database import База


class Уборка(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()

    def tearDown(self):
        self.папка.cleanup()

    def test_старое_убирается_новое_остаётся(self):
        with self.база.соединение() as с:
            с.execute("INSERT INTO аудит (действие, создано) VALUES ('старое', datetime('now','localtime','-400 days'))")
            с.execute("INSERT INTO аудит (действие) VALUES ('новое')")
            с.execute("INSERT INTO поиск_кэш (ключ, данные, создано) VALUES ('к', '[]', ?)", (time.time() - 30 * 86400,))
        итог = housekeeping.убрать(self.база, 180)
        self.assertEqual(итог["аудит"], 1)
        self.assertEqual(итог["поиск_кэш"], 1)
        with self.база.соединение() as с:
            self.assertEqual([r[0] for r in с.execute("SELECT действие FROM аудит")], ["новое"])

    def test_непрочитанная_доска_и_память_не_трогаются(self):
        with self.база.соединение() as с:
            с.execute("INSERT INTO доска (от, кому, текст, прочитано, создано) VALUES ('а','б','т',0, datetime('now','localtime','-400 days'))")
        housekeeping.убрать(self.база, 180)
        with self.база.соединение() as с:
            self.assertEqual(с.execute("SELECT COUNT(*) FROM доска").fetchone()[0], 1)

    def test_старые_файлы_логов(self):
        логи = Path(self.папка.name) / "logs"
        логи.mkdir()
        старый, главный = логи / "mizuyori.log.3", логи / "mizuyori.log"
        for ф in (старый, главный):
            ф.write_text("x")
        давно = time.time() - 400 * 86400
        import os
        os.utime(старый, (давно, давно)); os.utime(главный, (давно, давно))
        housekeeping.убрать(self.база, 180, логи)
        self.assertFalse(старый.exists())
        self.assertTrue(главный.exists())


class Регион(unittest.TestCase):
    def tearDown(self):
        senses.настроить_регион(проверить_агентов({}))

    def test_проверка_настроек(self):
        н = проверить_агентов({"регион": " Хабаровский край ", "хранить_дней": 5, "признаки_региона": ["Хабаровск", "х"]})
        self.assertEqual(н["регион"], "Хабаровский край")
        self.assertEqual(н["хранить_дней"], 180)
        self.assertEqual(н["признаки_региона"], ["хабаровск"])

    def test_регион_меняет_поиск(self):
        senses.настроить_регион(проверить_агентов({"регион": "Хабаровский край", "главный_город": "Хабаровск", "признаки_региона": ["хабаровск"]}))
        self.assertTrue(senses.из_приморья({"название": "Магазин Хабаровск", "кратко": "", "ссылка": "http://x.ru"}))
        self.assertFalse(senses.из_приморья({"название": "Владивосток авто", "кратко": "", "ссылка": "http://x.ru"}))


class Шаблоны(unittest.TestCase):
    def test_удалённый_готовый_шаблон_не_возвращается_а_новые_добавляются(self):
        с = tempfile.TemporaryDirectory()
        база = База(Path(с.name) / "t.db"); база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(база); missions.подключить(база)
        missions.заполнить_готовые()
        шаблон = next(ш for ш in missions.шаблоны() if ш["название"].startswith("ГСМ"))
        missions.удалить_шаблон(шаблон["id"])
        missions.заполнить_готовые()
        self.assertFalse(any(ш["название"].startswith("ГСМ") for ш in missions.шаблоны()))
        self.assertEqual(len(missions.шаблоны()), len(missions.ГОТОВЫЕ_ШАБЛОНЫ) - 1)
        с.cleanup()


if __name__ == "__main__":
    unittest.main()
