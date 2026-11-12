import sys
import unittest
from pathlib import Path

from mizuyori import mcp_client, tools

СЕРВЕР = str(Path(__file__).with_name("fake_mcp_server.py"))


class ТестMCP(unittest.TestCase):
    def setUp(self):
        self.состояние = {}
        mcp_client.подключить(lambda: dict(self.состояние), lambda з: self.состояние.update(з) or None)
        mcp_client.КАТАЛОГ["тест"] = {"имя": "Тест", "что": "проверка", "команда": [sys.executable, "-I", СЕРВЕР], "только_чтение": True}

    def tearDown(self):
        mcp_client.остановить_все()
        mcp_client.КАТАЛОГ.pop("тест", None)
        tools.сохранить_настройки({"только_чтение": False, "выключены": [], "агенты": {}})

    def test_включение_регистрирует_инструменты_и_вызывает(self):
        с = mcp_client.включить("тест", True)
        self.assertTrue(с["работает"])
        self.assertIn("тест.echo", tools.ИНСТРУМЕНТЫ)
        self.assertEqual(tools.ИНСТРУМЕНТЫ["тест.echo"].набор, "внешние")
        self.assertFalse(tools.рискованный("тест.echo"))
        итог = tools.вызвать("тест.echo", {"описание": "привет", "агент": "инженер"})
        self.assertIn("привет", итог)
        mcp_client.включить("тест", False)
        self.assertNotIn("тест.echo", tools.ИНСТРУМЕНТЫ)
        self.assertEqual(self.состояние["включены"], [])

    def test_адрес_из_внутренней_сети_блокируется(self):
        mcp_client.включить("тест", True)
        with self.assertRaises(PermissionError):
            tools.вызвать("тест.fetch", {"описание": "http://192.168.0.1/admin", "агент": "инженер"})
        self.assertIn("8.8.8.8", tools.вызвать("тест.fetch", {"описание": "прочитай https://8.8.8.8/x", "агент": "инженер"}))

    def test_выключатель_наборов_закрывает_внешние(self):
        mcp_client.включить("тест", True)
        tools.подключить(lambda: {"выключены": ["внешние"]}, lambda з: None)
        try:
            self.assertFalse(tools.разрешён("тест.echo", "инженер")[0])
        finally:
            tools.подключить(lambda: {}, lambda з: None)

    def test_нет_программы(self):
        mcp_client.КАТАЛОГ["тест"]["команда"] = ["нет-такой-программы-xyz"]
        with self.assertRaises(Exception):
            mcp_client.включить("тест", True)
        self.assertIn("не найдена", mcp_client.состояние("тест")["ошибка"])

    def test_сборка_аргументов(self):
        схема = {"properties": {"timezone": {"type": "string"}}, "required": ["timezone"]}
        self.assertEqual(mcp_client.собрать_аргументы(схема, "Который час в Asia/Vladivostok?"), {"timezone": "Asia/Vladivostok"})
        self.assertEqual(mcp_client.собрать_аргументы(схема, 'вызови {"timezone": "UTC"}'), {"timezone": "UTC"})


if __name__ == "__main__":
    unittest.main()
