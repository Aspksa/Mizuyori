import json
import tempfile
import time
import unittest
from pathlib import Path

from mizuyori import agents, ai, audit, chat_delegate, missions, tools, work_agents
from mizuyori.config import проверить_агентов
from mizuyori.database import База

Н = {"включён": True, "ключ": "k", "модель": "m", "адрес": "http://x", "история": 5}


class Передача(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(self.база); missions.подключить(self.база)
        audit.подключить(self.база)
        chat_delegate.подключить(self.база)
        chat_delegate.НАСТРОЙКИ = {"поручения_из_чата": "авто"}
        chat_delegate._ждёт = None
        chat_delegate._решения_хозяина.clear()
        self.разбор = {"поручение": True, "агент": "снабженец", "название": "Цена VIC C-111", "инструмент": "поиск",
                       "описание": "Найти цену на масляный фильтр VIC C-111 в интернете", "ожидание": "Три варианта с ценой"}
        self.вызовы = 0
        self.запуски = []
        self.старое = (ai._задание, missions.запустить)

        def ложный(система, данные, н, max_tokens):
            self.вызовы += 1
            return json.dumps(self.разбор, ensure_ascii=False)
        ai._задание = ложный
        missions.запустить = lambda номер, н: self.запуски.append(номер)

    def tearDown(self):
        ai._задание, missions.запустить = self.старое
        chat_delegate._ждёт = None
        self.t.cleanup()

    def test_обычный_разговор_не_тратит_вызов_ии(self):
        self.assertIsNone(chat_delegate.из_чата(self.база, Н, "как дела сегодня", []))
        self.assertEqual(self.вызовы, 0)

    def test_просьба_запускает_настоящее_поручение(self):
        р = chat_delegate.из_чата(self.база, Н, "пускай снабженец посмотрит цену", ["фильтр vic c 111"])
        self.assertIn("Передал", р[1])
        self.assertEqual(len(self.запуски), 1)
        м = missions.получить(self.запуски[0])
        self.assertEqual(m_агент(м), "снабженец")
        self.assertEqual(m_инструмент(м), "поиск")

    def test_не_просьба_по_решению_ии(self):
        self.разбор = {"поручение": False}
        self.assertIsNone(chat_delegate.из_чата(self.база, Н, "надо подумать об этом", []))
        self.assertEqual(self.запуски, [])

    def test_чужой_агент_и_запрещённый_инструмент_отсекаются(self):
        self.разбор["агент"] = "выдуманный"
        self.assertIsNone(chat_delegate.из_чата(self.база, Н, "найди цену на фильтр", []))
        self.разбор.update({"агент": "кадровик", "инструмент": "поиск"})      # кадровику поиск не положен
        р = chat_delegate.из_чата(self.база, Н, "найди цену на фильтр", [])
        self.assertEqual(m_инструмент(missions.получить(self.запуски[0])), "")

    def test_всегда_спрашивать_ждёт_да(self):
        chat_delegate.НАСТРОЙКИ = {"поручения_из_чата": "всегда_спрашивать"}
        р = chat_delegate.из_чата(self.база, Н, "найди цену на фильтр vic c-111", [])
        self.assertIn("да / нет", р[1])
        self.assertEqual(self.запуски, [])
        р = chat_delegate.из_чата(self.база, Н, "да", [])
        self.assertIn("Передал", р[1])
        self.assertEqual(len(self.запуски), 1)

    def test_нет_отменяет(self):
        chat_delegate.НАСТРОЙКИ = {"поручения_из_чата": "всегда_спрашивать"}
        chat_delegate.из_чата(self.база, Н, "найди цену на фильтр vic c-111", [])
        р = chat_delegate.из_чата(self.база, Н, "нет", [])
        self.assertIn("Отменено", р[1])
        self.assertEqual(self.запуски, [])

    def test_выкл(self):
        chat_delegate.НАСТРОЙКИ = {"поручения_из_чата": "выкл"}
        self.assertIsNone(chat_delegate.из_чата(self.база, Н, "найди цену на фильтр vic c-111", []))
        self.assertEqual(self.вызовы, 0)

    def test_итог_приходит_в_чат(self):
        chat_delegate.из_чата(self.база, Н, "найди цену на фильтр vic c-111", [])
        номер = self.запуски[0]
        missions._сохранить(номер, статус="готово", итог="Нашёл: 450 ₽ (ссылка)")
        chat_delegate._при_остановке(missions.получить(номер))
        последнее = self.база.сообщения(1)[-1]
        self.assertEqual(последнее["роль"], "ии")
        self.assertIn("450", последнее["текст"])
        self.assertNotIn(номер, chat_delegate._мои())

    def test_чужое_поручение_в_чат_не_пишет(self):
        м = missions.создать("Чужое", [{"агент": "снабженец", "описание": "что-то"}])
        missions._сохранить(м["id"], статус="готово", итог="итог")
        chat_delegate._при_остановке(missions.получить(м["id"]))
        self.assertEqual(self.база.сообщения(), [])

    def test_через_для_чата(self):
        р = work_agents.для_чата(self.база, Н, "проверь, чтобы юрист сверил сроки договоров на этой неделе")
        self.assertIn("Передал", р.get("сообщение", ""))
        self.assertEqual(len(self.запуски), 1)

    def test_ложное_обещание(self):
        self.assertTrue(chat_delegate.ложное_обещание("Передала снабженцу: запрос цены. Как ответит — сообщу."))
        self.assertTrue(chat_delegate.ложное_обещание("Хорошо, запущу проверку."))
        self.assertFalse(chat_delegate.ложное_обещание("VIC C-111 — масляный фильтр, подходит к Toyota."))

    def test_настройка_режима(self):
        self.assertEqual(проверить_агентов({"поручения_из_чата": "выкл"})["поручения_из_чата"], "выкл")
        self.assertEqual(проверить_агентов({"поручения_из_чата": "что-то"})["поручения_из_чата"], "авто")


def m_агент(м):
    return м["шаги"][0]["агент"]


def m_инструмент(м):
    return м["шаги"][0]["инструмент"]


if __name__ == "__main__":
    unittest.main()
