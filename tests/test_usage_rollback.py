import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from mizuyori import agents, ai, audit, evolve, usage
from mizuyori.database import База


class База_(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()
        agents.подключить(self.база)
        audit.подключить(self.база)
        usage.подключить(self.база)
        agents.ИМЕНА.setdefault("снабженец", "Снабженец")

    def tearDown(self):
        ai.при_расходе = None
        self.папка.cleanup()


class ТестРасхода(База_):
    def test_расход_записывается_на_текущего_агента(self):
        usage.записать(100)                                # вне «работы» — на чат
        with agents.работа("снабженец", "тест"):
            usage.записать(300)
            with agents.работа("память", "вложенная"):
                usage.записать(50)
            usage.записать(10)
        ai.установить_приоритет("фон")
        try:
            with agents.работа("память", "тест"):
                usage.записать(40, оценка=True)
        finally:
            ai.установить_приоритет("чат")
        о = usage.отчёт(7)
        по = {а["агент"]: а for а in о["по_агентам"]}
        self.assertEqual(по["чат"]["токенов"], 100)
        self.assertEqual(по["снабженец"]["токенов"], 310)
        self.assertEqual(по["память"]["токенов"], 90)
        self.assertEqual(по["память"]["в_фоне"], 40)
        self.assertEqual(о["всего"], 500)
        self.assertEqual(о["по_приоритетам"]["фон"], 40)
        self.assertEqual(о["по_агентам"][0]["агент"], "снабженец")

    def test_ai_пишет_расход_через_хук(self):
        старое = urllib.request.urlopen

        class Отв:
            def read(self):
                return json.dumps({"choices": [{"message": {"content": "ок"}}], "usage": {"total_tokens": 77}}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *а):
                pass
        urllib.request.urlopen = lambda *а, **к: Отв()
        try:
            with agents.работа("снабженец", "x"):
                ai._задание("с", {"a": 1}, {"адрес": "https://x", "ключ": "k", "модель": "m"}, 10)
        finally:
            urllib.request.urlopen = старое
        self.assertEqual({а["агент"]: а["токенов"] for а in usage.отчёт(1)["по_агентам"]}, {"снабженец": 77})


class ТестАвтоотката(База_):
    ключ = "снабженец"

    def оценки(self, балл, n):
        for и in range(n):
            evolve.записать_оценку(self.ключ, 1, и, "шаг", "прошёл" if балл == 1 else "ошибка", 1)

    def предложение(self):
        agents.сохранить_профиль(self.ключ, {"роль": "было"}, "старт")
        п = evolve._сохранить_предложение(self.ключ, "правило", "Всегда указывай цену", "тест", {"принять": True})
        return evolve.принять_предложение(п["id"])

    def test_падение_оценки_предлагает_откат_и_откатывает(self):
        self.оценки(1, 5)
        п = self.предложение()
        self.assertIsNotNone(evolve._получить(п["id"])["откат_к"])
        self.assertEqual(evolve._получить(п["id"])["оценка_до"], 1.0)
        self.assertEqual(evolve.проверить_откаты(), [])             # новых оценок ещё нет
        self.оценки(0, 5)
        предложены = evolve.проверить_откаты(self.ключ)
        self.assertEqual(len(предложены), 1)
        self.assertEqual(предложены[0]["откат_статус"], "предложен")
        self.assertTrue(any(з["текст"] == "Всегда указывай цену" for з in agents.заметки(self.ключ)))
        итог = evolve.откатить_улучшение(п["id"])
        self.assertEqual(итог["предложение"]["откат_статус"], "выполнен")
        self.assertFalse(any(з["текст"] == "Всегда указывай цену" for з in agents.заметки(self.ключ)))
        self.assertIsNone(evolve.откатить_улучшение(п["id"]))

    def test_без_падения_откат_не_предлагается(self):
        self.оценки(1, 5)
        п = self.предложение()
        self.оценки(1, 10)
        self.assertEqual(evolve.проверить_откаты(), [])
        self.assertEqual(evolve._получить(п["id"])["откат_статус"], "оставлено")

    def test_оставить(self):
        self.оценки(1, 5)
        п = self.предложение()
        self.оценки(0, 5)
        evolve.проверить_откаты()
        self.assertEqual(evolve.оставить_улучшение(п["id"])["откат_статус"], "оставлено")
        self.assertTrue(any(з["текст"] == "Всегда указывай цену" for з in agents.заметки(self.ключ)))


if __name__ == "__main__":
    unittest.main()
