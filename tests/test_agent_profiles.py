import tempfile
import unittest
from pathlib import Path

from mizuyori import agent_profiles, agents, overseer, work_agents
from mizuyori.database import База


class Профили(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(self.база)

    def tearDown(self):
        self.t.cleanup()

    def test_у_всех_агентов_есть_профиль_в_пределах(self):
        for а in agents.АГЕНТЫ:
            if а["ключ"] == "смотрящий" or а["ключ"] in agents.ИМЕНА:
                self.assertIn(а["ключ"], agent_profiles.ПРОФИЛИ, а["ключ"])
        for ключ, поля in agent_profiles.ПРОФИЛИ.items():
            self.assertEqual(set(поля), {"роль", "цель", "предыстория", "указания"})
            for з in поля.values():
                self.assertTrue(0 < len(з) <= agents.ПРЕДЕЛ_ПОЛЯ, (ключ, len(з)))

    def test_свои_правки_не_затираются(self):
        agent_profiles.заполнить()
        agents.сохранить_профиль("юрист", {"роль": "моя роль"})
        agent_profiles.заполнить()
        self.assertEqual(agents.профиль("юрист")["роль"], "моя роль")


if __name__ == "__main__":
    unittest.main()
