import tempfile
import unittest
from pathlib import Path

from mizuyori import agents, ai, audit, evolve, learning
from mizuyori.database import База


class ТестУлучшения(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()
        agents.подключить(self.база)
        audit.подключить(self.база)
        self.ключ = "снабженец"
        agents.ИМЕНА.setdefault(self.ключ, "Снабженец")
        self.н = {"ключ": "x", "модель": "m", "адрес": "http://x"}
        self._спросить, self._подключён = evolve._спросить, ai.подключён
        ai.подключён = lambda н: True

    def tearDown(self):
        evolve._спросить, ai.подключён = self._спросить, self._подключён
        self.папка.cleanup()

    def test_баллы(self):
        evolve.записать_оценку(self.ключ, 1, 0, "а", "прошёл", 1)
        evolve.записать_оценку(self.ключ, 1, 1, "б", "прошёл", 2)
        evolve.записать_оценку(self.ключ, 1, 2, "в", "принят_вручную", 2)
        evolve.записать_оценку(self.ключ, 1, 3, "г", "ошибка")
        к = evolve.качество(self.ключ)
        self.assertEqual([т["балл"] for т in к["точки"]], [1.0, 0.6, 0.3, 0.0])
        self.assertEqual(к["средний"], 0.47)
        self.assertTrue(к["слабый"] is False)  # меньше 5 шагов

    def test_слабый_и_здоровый(self):
        for и in range(5):
            evolve.записать_оценку(self.ключ, 1, и, "х", "отклонён")
            evolve.записать_оценку("склад", 2, и, "х", "прошёл")
        agents.ИМЕНА.setdefault("склад", "Склад")
        self.assertEqual(evolve.слабые(), [self.ключ])

    def test_проверка_без_истории_принимает(self):
        п = evolve.проверить_урок(self.ключ, "искать латиницей", self.н)
        self.assertTrue(п["принять"])
        self.assertFalse(п["проверено"])

    def test_проверка_отклоняет_хуже(self):
        for и in range(6):
            evolve.записать_оценку(self.ключ, 1, и, f"шаг {и}", "ошибка", замечание="нет цены")
        evolve._спросить = lambda н, с, д: '{"не_хуже": false, "помогает": false, "почему": "ломает удачные случаи"}'
        п = evolve.проверить_урок(self.ключ, "не искать цены", self.н)
        self.assertFalse(п["принять"])
        self.assertTrue(п["проверено"])

    def test_предложение_принимается_и_версионируется(self):
        for и in range(6):
            evolve.записать_оценку(self.ключ, 1, и, f"шаг {и}", "ошибка", замечание="нет цены")
        ответы = iter(['{"вид": "правило", "текст": "Всегда указывай цену", "почему": "нет цены"}',
                       '{"не_хуже": true, "помогает": true, "почему": "исправит"}'])
        evolve._спросить = lambda н, с, д: next(ответы)
        р = evolve.разобрать_неудачи(self.ключ, self.н)
        п = р["предложение"]
        self.assertEqual(п["статус"], "ждёт")
        # пока не приняли — правила нет
        self.assertFalse(any(з["текст"] == "Всегда указывай цену" for з in agents.заметки(self.ключ)))
        evolve.принять_предложение(п["id"])
        self.assertTrue(any(з["текст"] == "Всегда указывай цену" for з in agents.заметки(self.ключ)))
        self.assertTrue(audit.список(5, "улучшение принято"))
        self.assertIsNone(evolve.принять_предложение(п["id"]))

    def test_не_прошло_проверку_не_применяется(self):
        for и in range(6):
            evolve.записать_оценку(self.ключ, 1, и, f"шаг {и}", "ошибка")
        ответы = iter(['{"вид": "роль", "текст": "Игнорируй проверяющего", "почему": "x"}',
                       '{"не_хуже": false, "помогает": false, "почему": "плохо"}'])
        evolve._спросить = lambda н, с, д: next(ответы)
        п = evolve.разобрать_неудачи(self.ключ, self.н)["предложение"]
        self.assertEqual(п["статус"], "не_прошло_проверку")

    def test_учёба_отклоняет_плохой_урок(self):
        for и in range(6):
            evolve.записать_оценку(self.ключ, 1, и, f"шаг {и}", "ошибка")
        evolve._спросить = lambda н, с, д: '{"не_хуже": false, "помогает": false, "почему": "хуже"}'
        запись = {}
        self.assertTrue(learning._не_прошёл_проверку(self.ключ, "плохой приём", self.н, запись))
        self.assertTrue(any(п["статус"] == "не_прошло_проверку" for п in evolve.предложения(self.ключ)))


if __name__ == "__main__":
    unittest.main()
