import json
import re
import tempfile
import unittest
from pathlib import Path

from mizuyori import agents, ai, audit, chat_delegate, collective, decisions, learning, missions, work_agents
from mizuyori.database import База

Н = {"включён": True, "ключ": "k", "модель": "m", "адрес": "http://x", "история": 5}


class Решения(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        decisions.подключить(self.база)

    def tearDown(self):
        self.t.cleanup()

    def test_нет_данных_определяется_и_считается(self):
        номер = decisions.записать("ответ", "сколько налог", ["налоги"], ["работа"], "Нет данных: не хватает ставки.")
        self.assertEqual(decisions.журнал_записей(1)[0]["статус"], "нет данных")
        self.assertGreater(номер, 0)
        self.assertEqual(decisions.качество()["налоги"]["без_данных"], 1)

    def test_поправка_помечает_последний_ответ(self):
        номер = decisions.записать("ответ", "вопрос", ["чат"], [], "ответ")
        self.assertEqual(decisions.поправка("нет, не так", learning._ПОПРАВКА), номер)
        self.assertEqual(decisions.журнал_записей(1)[0]["статус"], "исправлено")
        self.assertEqual(decisions.поправка("спасибо", learning._ПОПРАВКА), 0)

    def test_доля_ошибок_только_после_трёх_ответов(self):
        for и in range(2):
            decisions.записать("ответ", f"в{и}", ["чат"], [], "ок")
        decisions.поправка("неверно", learning._ПОПРАВКА)
        self.assertIsNone(decisions.качество()["чат"]["доля_ошибок"])
        decisions.записать("ответ", "в3", ["чат"], [], "ок")
        self.assertEqual(decisions.качество()["чат"]["доля_ошибок"], 0.33)

    def test_журнал_не_растёт_бесконечно(self):
        for и in range(decisions.МАКС_ЗАПИСЕЙ + 20):
            decisions.записать("ответ", str(и), ["чат"], [], "ок")
        self.assertEqual(len(decisions.журнал_записей(1000)), decisions.МАКС_ЗАПИСЕЙ)


class Коллектив(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(self.база); missions.подключить(self.база)
        audit.подключить(self.база); decisions.подключить(self.база); chat_delegate.подключить(self.база)
        chat_delegate.НАСТРОЙКИ = {"поручения_из_чата": "авто"}
        self.вызовы = []
        self.запуски = []
        self.старое = (ai._задание, missions.запустить)

        def ложный(система, данные, н, max_tokens):
            self.вызовы.append(система[:30])
            if "Раздели её" in система:
                люди = [л["ключ"] for л in данные["сотрудники"]]
                return json.dumps({"название": "Подготовить сверку", "шаги": [
                    {"агент": люди[0], "описание": "Собрать данные", "ожидание": "Таблица"},
                    {"агент": "выдуманный", "описание": "Лишний шаг"},
                    {"агент": люди[-1], "описание": "Проверить итоги", "ожидание": "Без ошибок"}]}, ensure_ascii=False)
            if "Сведи их" in система:
                return "Общий вывод: надо проверить. Бухгалтерия: нет данных."
            return "Мнение кабинета: проверить сроки."
        ai._задание = ложный
        missions.запустить = lambda номер, н: self.запуски.append(номер)

    def tearDown(self):
        ai._задание, missions.запустить = self.старое
        self.t.cleanup()

    def test_разбор_поручения_кабинету(self):
        self.assertEqual(collective.поручение_кабинету("поручи бухгалтерии подготовить сверку по налогам"),
                         ("бухгалтерия", "подготовить сверку по налогам"))
        self.assertEqual(collective.поручение_кабинету("пускай юристам проверят договор аренды")[0], "юристы")
        self.assertIsNone(collective.поручение_кабинету("поручи бухгалтеру найти счёт"))
        self.assertIsNone(collective.поручение_кабинету("пускай механик посмотрит насос"))
        self.assertEqual(collective.поручение_кабинету("поручи кабинету механика проверить склад")[0], "механик")

    def test_совещание_только_по_явной_просьбе(self):
        self.assertTrue(collective.это_совещание("Проведи совещание: брать ли машину в лизинг"))
        self.assertFalse(collective.это_совещание("как дела сегодня"))
        self.assertIsNone(collective.из_чата(self.база, Н, "как дела сегодня"))

    def test_совещание_собирает_мнения_и_пишет_журнал(self):
        запись = decisions.записать("совещание", "лизинг", [], [], "", статус="в работе")
        итог = collective.провести_совещание(self.база, Н, "брать ли машину в лизинг", ["бухгалтерия", "юристы"], запись)
        self.assertIn("Итог совещания", итог)
        z = decisions.журнал_записей(1)[0]
        self.assertEqual(z["статус"], "нет данных")
        записки = agents.доска()
        self.assertEqual({з["от"] for з in записки}, {collective.руководитель("бухгалтерия"), collective.руководитель("юристы")})
        self.assertTrue(all(з["кому"] == "чат" for з in записки))

    def test_кабинет_разбивает_задачу_на_шаги_своих(self):
        текст = collective.запустить_кабинету(self.база, Н, "бухгалтерия", "подготовить сверку по налогам")
        self.assertIn("разбил задачу", текст)
        self.assertEqual(len(self.запуски), 1)
        м = missions.получить(self.запуски[0])
        агенты_шагов = [ш["агент"] for ш in м["шаги"]]
        self.assertEqual(len(агенты_шагов), 2)                       # выдуманный исполнитель отброшен
        каб = {а["ключ"] for а in agents.АГЕНТЫ if а.get("кабинет") == "бухгалтерия"}
        self.assertTrue(set(агенты_шагов) <= каб)
        self.assertIn(self.запуски[0], chat_delegate._мои())
        з = decisions.журнал_записей(1)[0]
        self.assertEqual((з["вид"], з["статус"], з["поручение"]), ("кабинет", "в работе", self.запуски[0]))

    def test_остановка_поручения_закрывает_запись_журнала(self):
        collective.запустить_кабинету(self.база, Н, "бухгалтерия", "подготовить сверку по налогам")
        номер = self.запуски[0]
        chat_delegate._в_журнал({"id": номер, "статус": "готово"}, "Всё посчитано")
        self.assertEqual(decisions.журнал_записей(1)[0]["статус"], "принято")
        chat_delegate._в_журнал({"id": номер, "статус": "не вышло"}, "Сбой")
        self.assertEqual(decisions.журнал_записей(1)[0]["статус"], "не вышло")


if __name__ == "__main__":
    unittest.main()
