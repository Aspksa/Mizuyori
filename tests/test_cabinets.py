"""Кабинеты: у каждого агента есть место в структуре, профиль и наблюдатель, а наблюдатели не падают на пустой базе."""
import tempfile
import unittest
from pathlib import Path

from mizuyori import agent_profiles, agents, cabinets, work_agents
from mizuyori.database import База


class ТестКабинетов(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work_agents.зарегистрировать()
        cls.ключи = [а["ключ"] for а in agents.АГЕНТЫ]
        cls.папка = tempfile.mkdtemp()
        cls.база = База(Path(cls.папка) / "т.db")
        cls.база.подготовить()
        agents.подключить(cls.база)

    def test_каждый_агент_один_раз_в_кабинете(self):
        где = [к for каб in cabinets.КАБИНЕТЫ for о in каб["отделы"] for к in о["агенты"]]
        self.assertEqual(len(где), len(set(где)), "агент в двух отделах")
        self.assertEqual(set(где), set(self.ключи))

    def test_руководители_и_верх_существуют(self):
        for каб in cabinets.КАБИНЕТЫ:
            self.assertIn(каб["верх"], self.ключи)
            for о in каб["отделы"]:
                if о["руководитель"]:
                    self.assertIn(о["руководитель"], о["агенты"])

    def test_у_каждого_есть_профиль_и_наблюдатель(self):
        for к in self.ключи:
            self.assertIn(к, agent_profiles.ПРОФИЛИ, f"нет профиля: {к}")
            if к not in ("чат", "память", "смысл", "сводка", "цели", "мнения"):
                self.assertIn(к, work_agents.НАБЛЮДАТЕЛИ, f"нет наблюдателя: {к}")

    def test_наблюдатели_на_пустой_базе(self):
        for к, наблюдать in cabinets.НАБЛЮДАТЕЛИ.items():
            итог = наблюдать(self.база)
            self.assertIsInstance(итог, list, к)

    def test_переименованные_не_дублируются(self):
        имена = [agents.ИМЕНА[к] for к in self.ключи]
        self.assertEqual(len(имена), len(set(имена)), "одинаковые имена у разных агентов")
        self.assertEqual(agents.ИМЕНА["бухгалтер"], "Бухгалтер по поставщикам")

    def test_структура_для_схемы(self):
        схема = cabinets.структура()
        self.assertEqual([к["ключ"] for к in схема], ["бухгалтерия", "механик", "экономисты", "юристы", "штаб"])


if __name__ == "__main__":
    unittest.main()
