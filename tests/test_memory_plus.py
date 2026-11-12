import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from mizuyori import agents, audit, memory, memory_plus
from mizuyori.database import База


class ТестПамятиПлюс(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()
        agents.подключить(self.база)
        audit.подключить(self.база)
        self.н = {}

    def tearDown(self):
        self.папка.cleanup()

    def заполнить(self, n=20):
        for и in range(n):
            self.база.запомнить(f"Вспомогательный факт номер {и} про погоду и кофе", None, "другое", 2)

    def test_артикул_ловится_словами(self):
        self.заполнить()
        self.база.запомнить("Для Hilux беру воздушный фильтр VIC C-111", None, "работа", 3)
        найдено = memory.выбрать_факты(self.база, self.н, "что за фильтр C111", 3)
        self.assertTrue(any("C-111" in ф["факт"] for ф in найдено))

    def test_bm25_и_основы(self):
        оценки = memory_plus.bm25("маме подарок", ["Мама любит чай", "Работа в гараже"])
        self.assertGreater(оценки[0], оценки[1])

    def test_намерение_времени(self):
        self.assertEqual(memory_plus.намерение_времени("где я работаю сейчас"), "сейчас")
        self.assertEqual(memory_plus.намерение_времени("что было раньше"), "прошлое")
        self.assertEqual(memory_plus.намерение_времени("что я планирую"), "будущее")
        self.assertEqual(memory_plus.намерение_времени("привет"), "")

    def test_прошлое_добавляет_устаревшие(self):
        self.заполнить()
        старый = self.база.запомнить("Раньше жил в Находке", None, "о себе", 3)
        memory_plus.архивировать(self.база, старый["id"], "переехал")
        найдено = memory.выбрать_факты(self.база, self.н, "где я жил раньше в Находке", 5)
        self.assertTrue(any(ф["факт"].startswith("(устарело)") and "Находке" in ф["факт"] for ф in найдено))
        без = memory.выбрать_факты(self.база, self.н, "где я живу в Находке", 5)
        self.assertFalse(any("Находке" in ф["факт"] for ф in без))

    def test_архив_возврат_и_история(self):
        ф = self.база.запомнить("Факт А", None, "другое", 2)
        self.assertTrue(memory_plus.архивировать(self.база, ф["id"], "тест"))
        self.assertEqual(self.база.факт(ф["id"])["состояние"], "архив")
        self.assertEqual(memory_plus.восстановить(self.база, ф["id"])["состояние"], "активен")
        self.база.изменить_факт(ф["id"], {"факт": "Факт Б"}, "уточнено")
        версии = memory_plus.история_факта(self.база, ф["id"])
        self.assertTrue(any(в["текст"] == "Факт А" and в["причина"] == "уточнено" for в in версии))

    def test_очередь_предложений(self):
        memory_plus.включить_подтверждение(self.база, True)
        self.assertTrue(memory_plus.нужно_подтверждение(self.база))
        п = memory_plus.предложить(self.база, "Любит зелёный чай", "предпочтения", 3)
        self.assertIsNone(memory_plus.предложить(self.база, "Любит зелёный чай"))   # без дублей
        self.assertEqual(len(self.база.память()), 0)
        memory_plus.принять(self.база, п["id"])
        self.assertEqual([ф["факт"] for ф in self.база.память()], ["Любит зелёный чай"])
        self.assertIsNone(memory_plus.принять(self.база, п["id"]))

    def test_обобщение_архивирует_старые(self):
        а = self.база.запомнить("Пьёт чай утром", None, "другое", 2)
        б = self.база.запомнить("Пьёт чай вечером", None, "другое", 2)
        п = memory_plus.предложить(self.база, "Пьёт чай утром и вечером", "другое", 3, None, "обобщение", [а["id"], б["id"]])
        memory_plus.принять(self.база, п["id"])
        активные = [ф["факт"] for ф in self.база.память()]
        self.assertEqual(активные, ["Пьёт чай утром и вечером"])

    def test_слабое_забывается_важное_нет(self):
        сильные = self.база.запомнить("Срок ТО грузовика — март", None, "работа", 2)
        слабое = self.база.запомнить("Видел голубя", None, "другое", 1)
        важное = self.база.запомнить("Живу во Владивостоке", None, "о себе", 5)
        давно = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
        with self.база.соединение() as с:
            с.execute("UPDATE память SET создано = ?, изменено = ?", (давно, давно))
        ушли = memory_plus.забыть_слабое(self.база)
        self.assertEqual([ф["id"] for ф in ушли], [слабое["id"]])
        self.assertEqual(self.база.факт(слабое["id"])["состояние"], "архив")
        self.assertEqual(self.база.факт(важное["id"])["состояние"], "активен")
        self.assertEqual(self.база.факт(сильные["id"])["состояние"], "активен")

    def test_слияние_точных_повторов(self):
        a = self.база.запомнить("Любит чай!", None, "другое", 2)
        with self.база.соединение() as с:
            с.execute("INSERT INTO память (факт, важность) VALUES ('любит  чай', 3)")
        self.assertEqual(memory_plus.слить_дубли(self.база), 1)
        self.assertEqual(len(self.база.память()), 1)


if __name__ == "__main__":
    unittest.main()
