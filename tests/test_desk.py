import tempfile
import time
import unittest
from pathlib import Path

from mizuyori import agent_profiles, agents, audit, desk, missions, work_agents
from mizuyori.database import База


class Стол(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(self.база); missions.подключить(self.база); audit.подключить(self.база)
        agent_profiles.заполнить()

    def tearDown(self):
        self.t.cleanup()

    def test_снимок(self):
        agents.написать("снабженец", "юрист", "проверь договор")
        audit.записать("шаг подтверждён", "Закупка")
        м = missions.создать("Ждущее", [{"агент": "снабженец", "описание": "найти"}])
        missions._сохранить(м["id"], статус="ждёт вас")
        с = desk.снимок(self.база, {"поручения_из_чата": "авто"})
        self.assertEqual(sum(1 for а in с["агенты"] if а["лидер"]), 1)
        self.assertTrue(all(а["роль"] for а in с["агенты"]))
        self.assertEqual([п["номер"] for п in с["ждёт"]], [м["id"]])
        типы = {е["тип"] for е in с["события"]}
        self.assertIn("записка", типы)
        self.assertIn("да", типы)
        self.assertTrue(any("в час" in п["текст"] for п in с["правила"]))

    def test_следующий_обход(self):
        work_agents.СЛЕДУЮЩИЙ_ОБХОД = time.time() + 120
        с = desk.снимок(self.база, {})
        self.assertTrue(100 <= с["тик"]["через"] <= 120)
        work_agents.СЛЕДУЮЩИЙ_ОБХОД = 0.0


if __name__ == "__main__":
    unittest.main()
