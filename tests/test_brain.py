import tempfile
import unittest
from pathlib import Path

from mizuyori import ai, brain, memory
from mizuyori.database import База


class BackgroundBrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = База(Path(self.temp.name) / "test.db")
        self.db.подготовить()

    def tearDown(self):
        self.temp.cleanup()

    def test_safe_maintenance_without_ai(self):
        alice = self.db.сущность_или_новая("Алиса", "человек", другие_имена=["подруга"])
        with self.db.соединение() as связь:
            копия_id = связь.execute(
                "INSERT INTO сущности (имя, ключ, тип, другие_имена) VALUES (?, ?, ?, ?)",
                ("Лиса", "лиса", "человек", '["подруга"]')).lastrowid
        self.db.сущность_или_новая("Выучить японский", "цель")
        задача = self.db.добавить_задачу("Купить учебник")
        self.db.изменить_задачу(задача["id"], {"цель_id": копия_id})

        факт = self.db.запомнить("Алиса любит чай", категория="люди", важность=3)
        истёк = self.db.запомнить("Старая встреча завтра", категория="даты", важность=2)
        self.db.изменить_факт(истёк["id"], {"действует_до": "2000-01-01"})
        with self.db.соединение() as связь:
            повтор_id = связь.execute(
                "INSERT INTO память (факт, категория, важность, смысл) VALUES (?, ?, ?, ?)",
                ("Алиса любит чай!", "люди", 4, "{}")).lastrowid
            связь.execute("INSERT INTO отношения (от_id, отношение, к_id) VALUES (?, ?, ?)",
                          (alice["id"], "знает", alice["id"]))

        self.db.добавить_сообщение("ии", "Я проверю этот вопрос и вернусь с ответом")
        self.db.добавить_сообщение("пользователь", "Нет, неправильно: я обычно пью чай утром")
        self.db.добавить_сообщение("пользователь", "Я обычно пью чай утром")

        результат = brain.обслужить_в_фоне(
            self.db, {"ключ": "", "модель_эмбеддингов": ""}, принудительно=True)

        self.assertEqual(результат["истекло"], 1)
        self.assertEqual(результат["повторов_фактов"], 1)
        self.assertEqual(результат["повторов_сущностей"], 1)
        self.assertEqual(результат["граф_очищен"], 1)
        self.assertGreaterEqual(результат["целей_без_шага"], 1)
        self.assertEqual(self.db.факт(истёк["id"])["состояние"], "устарел")
        активный = next(ф for ф in self.db.память() if "любит чай" in ф["факт"])
        устаревший_id = факт["id"] if активный["id"] == повтор_id else повтор_id
        self.assertEqual(self.db.факт(устаревший_id)["состояние"], "устарел")
        self.assertIn(alice["id"], активный["сущности"])
        self.assertIsNone(self.db.сущность(копия_id))
        self.assertEqual(self.db.задача(задача["id"])["цель_id"], alice["id"])
        for вид in ("обещание", "исправление", "привычка"):
            self.assertTrue(self.db.наблюдения(вид))

        for _ in range(5):
            memory.выбрать_факты(self.db, {"ключ": "", "модель_эмбеддингов": ""}, "чай")
        использован = self.db.факт(активный["id"])
        self.assertGreaterEqual(использован["использовано"], 5)
        self.assertGreaterEqual(использован["важность"], 4)

    def test_high_confidence_analysis_is_applied(self):
        алиса = self.db.сущность_или_новая("Алиса", "человек")
        старый = self.db.запомнить("Алиса любит чай", категория="люди")
        новый = self.db.запомнить("Алиса больше не любит чай", категория="люди")
        первая = self.db.добавить_задачу("Получить разрешение")
        вторая = self.db.добавить_задачу("Начать работу")
        анализ = {
            "duplicates": [],
            "contradictions": [{"older_id": старый["id"], "newer_id": новый["id"],
                                "confidence": 0.95, "explanation": "предпочтение изменилось"}],
            "validity": [], "aliases": [], "entity_merges": [],
            "missing_links": [{"fact_id": новый["id"], "entity_id": алиса["id"], "confidence": 0.9}],
            "goal_gaps": [],
            "dependencies": [{"task_id": вторая["id"], "depends_on_id": первая["id"],
                              "reason": "нужно разрешение", "confidence": 0.9}],
            "promises": [], "habits": [], "corrections": [],
            "code_suggestions": [{"suggestion": "Оптимизировать индекс", "confidence": 0.8}],
        }

        результат = brain._применить_анализ(self.db, анализ)

        self.assertEqual(результат["факты"], 1)
        self.assertEqual(self.db.факт(старый["id"])["состояние"], "устарел")
        self.assertEqual(self.db.факт(старый["id"])["заменён_на"], новый["id"])
        self.assertEqual(len(self.db.зависимости_задач()), 1)
        понимание = memory.блок_понимания(
            self.db, {"ключ": "", "модель_эмбеддингов": ""}, "Что мешает начать работу?")
        self.assertIn("ждёт «Получить разрешение»", понимание)
        self.assertEqual(self.db.наблюдения("предложение_кода")[0]["текст"], "Оптимизировать индекс")

    def test_ai_response_is_strictly_filtered(self):
        исходное = ai._задание
        try:
            ai._задание = lambda *args, **kwargs: (
                '{"duplicates":[{"primary_id":1,"duplicate_id":2,"confidence":0.99}],'
                '"habits":[{"text":"любит чай","confidence":0.9}]}')
            результат = ai.осмыслить_мозг({}, {})
        finally:
            ai._задание = исходное
        self.assertEqual(результат["duplicates"][0]["primary_id"], 1)
        self.assertEqual(результат["habits"][0]["text"], "любит чай")
        self.assertEqual(результат["corrections"], [])


if __name__ == "__main__":
    unittest.main()
