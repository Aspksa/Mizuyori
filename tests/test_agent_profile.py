import tempfile
import unittest
from pathlib import Path

from mizuyori import agents
from mizuyori.database import База


class ПрофильАгента(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = База(Path(self.temp.name) / "t.db")
        self.db.подготовить()
        agents.подключить(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_пустой_профиль_ничего_не_добавляет(self):
        self.assertEqual(agents.правила("снабженец"), "")

    def test_профиль_попадает_в_задание_до_правил(self):
        agents.сохранить_профиль("снабженец", {"роль": "опытный снабженец", "цель": "найти подешевле", "предыстория": "", "указания": ""})
        agents.добавить_заметку("снабженец", "правило", "всегда сравнивай три магазина")
        т = agents.правила("снабженец")
        self.assertIn("Твоя роль: опытный снабженец", т)
        self.assertIn("Твоя цель: найти подешевле", т)
        self.assertLess(т.index("Твоя роль"), т.index("сравнивай три магазина"))

    def test_длинное_поле_обрезается_и_очистка_работает(self):
        agents.сохранить_профиль("юрист", {"роль": "я" * 2000})
        self.assertEqual(len(agents.профиль("юрист")["роль"]), agents.ПРЕДЕЛ_ПОЛЯ)
        agents.сохранить_профиль("юрист", {})
        self.assertEqual(agents.правила("юрист"), "")


if __name__ == "__main__":
    unittest.main()
