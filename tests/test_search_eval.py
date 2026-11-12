import tempfile
import unittest
from pathlib import Path

from mizuyori import agents, search_eval
from mizuyori.database import База


def р(название, ссылка="https://shop.example/x", кратко=""):
    return {"название": название, "ссылка": ссылка, "кратко": кратко}


class ТестПроверкиПоиска(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()
        agents.подключить(self.база)
        self._искать = search_eval.senses.искать_для_закупки

    def tearDown(self):
        search_eval.senses.искать_для_закупки = self._искать
        self.папка.cleanup()

    def test_оценка_запроса(self):
        пример = {"запрос": "фильтр VIC C-111", "артикул": "C-111"}
        self.assertEqual(search_eval.оценить_запрос(пример, [р("Фильтр VIC C111 воздушный")]), 1.0)
        self.assertEqual(search_eval.оценить_запрос(пример, [р("a"), р("b"), р("c"), р("VIC C-111")]), 0.5)
        self.assertEqual(search_eval.оценить_запрос(пример, [р("ничего")]), 0.0)
        слова = {"запрос": "шины", "слова": ["265/65", "r17"]}
        self.assertEqual(search_eval.оценить_запрос(слова, [р("Шины 265/65 R17 Nokian")]), 1.0)

    def test_сравнение_с_прошлым(self):
        набор = [{"запрос": "фильтр", "артикул": "C-111"}, {"запрос": "шины", "слова": ["r17"]}]
        search_eval.senses.искать_для_закупки = lambda з, а, получить=None, сколько=8: ([р("VIC C-111"), р("шины R17")], [з])
        первый = search_eval.прогнать(набор=набор)
        self.assertEqual(первый["балл"], 1.0)
        self.assertIn("точка отсчёта", первый["вердикт"])
        search_eval.senses.искать_для_закупки = lambda з, а, получить=None, сколько=8: ([р("мусор")], [з])
        второй = search_eval.прогнать(набор=набор)
        self.assertEqual(второй["балл"], 0.0)
        self.assertIn("хуже", второй["вердикт"])
        self.assertEqual(len(search_eval.история()), 2)

    def test_все_упали(self):
        def упал(*а, **к):
            raise OSError("нет сети")
        search_eval.senses.искать_для_закупки = упал
        итог = search_eval.прогнать(набор=[{"запрос": "x", "слова": ["x"]}])
        self.assertEqual(итог["ошибок"], 1)
        self.assertIn("не отвечает", итог["вердикт"])


if __name__ == "__main__":
    unittest.main()
