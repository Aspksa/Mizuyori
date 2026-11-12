import tempfile
import unittest
from pathlib import Path

from mizuyori import agents, audit, knowledge, learning, missions, work_agents
from mizuyori.database import База


class Знания(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.база = База(Path(self.t.name) / "t.db"); self.база.подготовить()
        work_agents.зарегистрировать(); agents.подключить(self.база); missions.подключить(self.база); audit.подключить(self.база)
        with learning._замок:
            learning._ожидают.clear()

    def tearDown(self):
        self.t.cleanup()

    # --- 6. личные факты агента
    def test_факты_подходящие_идут_первыми_и_лишнее_не_раздувает_задание(self):
        for т in ("Для Hilux берём фильтры VIC", "Шины покупаем у Колеса-Дв", "Шиномонтаж только по договору", "Масло Лукойл 5W-40",
                  "Щётки стеклоочистителя берём зимние", "Антифриз красный", "Аккумуляторы только свежие"):
            knowledge.добавить_факт("снабженец", т)
        выбранные = knowledge.факты_для("снабженец", "нужны шины на Hino", 3)
        self.assertEqual(len(выбранные), 3)
        self.assertIn("шины", выбранные[0]["текст"].lower())

    def test_факт_одного_агента_не_виден_другому_и_повтор_не_дублируется(self):
        knowledge.добавить_факт("снабженец", "Для Hilux берём фильтры VIC")
        self.assertTrue(knowledge.добавить_факт("снабженец", "для hilux берём фильтры vic")["уже_есть"])
        self.assertEqual(len(knowledge.факты("снабженец")), 1)
        self.assertEqual(knowledge.факты("юрист"), [])
        self.assertIn("Hilux", agents.правила("снабженец", "фильтр на Hilux"))
        self.assertNotIn("Hilux", agents.правила("юрист", "фильтр на Hilux"))

    def test_пустой_факт_отклоняется_и_удаление_работает(self):
        with self.assertRaises(ValueError):
            knowledge.добавить_факт("снабженец", "   ")
        ф = knowledge.добавить_факт("снабженец", "Факт")
        self.assertTrue(knowledge.удалить_факт(ф["id"]))
        self.assertFalse(knowledge.удалить_факт(ф["id"]))

    # --- 10. общий справочник
    def test_справочник_по_алиасу_и_госномеру_для_любого_агента(self):
        with self.база.соединение() as с:
            с.execute("INSERT INTO раб_автомобили (марка, модель, госномер, топливо) VALUES ('Toyota', 'Hilux', 'А123ВС', 'ДТ')")
        knowledge.добавить("техника", "Toyota Hilux", "хайлюкс, белый пикап", "возит бригаду мостовиков")
        для_юриста = agents.правила("юрист", "страховка на хайлюкс")
        self.assertIn("Toyota Hilux", для_юриста)
        self.assertIn("возит бригаду мостовиков", для_юриста)
        self.assertIn("ДТ", для_юриста)                       # живые данные склеились с ручной записью
        self.assertIn("Toyota Hilux", agents.правила("снабженец", "фильтр для а 123 вс"))
        self.assertEqual(knowledge.найти("погода во Владивостоке"), [])

    def test_контрагент_из_работы_виден_по_названию_и_инн(self):
        with self.база.соединение() as с:
            с.execute("INSERT INTO раб_контрагенты (название, инн, контакт) VALUES ('Колесо-Дв', '2540123456', 'Игорь')")
        self.assertEqual(knowledge.найти("счёт от колесо-дв")[0]["название"], "Колесо-Дв")
        self.assertEqual(knowledge.найти("ИНН 2540123456")[0]["название"], "Колесо-Дв")
        self.assertIn("Игорь", knowledge.справка("колесо-дв"))

    def test_короткие_имена_не_цепляются_за_чужие_слова(self):
        knowledge.добавить("другое", "ТО", "", "техобслуживание")
        self.assertEqual(knowledge.найти("потолок"), [])

    def test_справочник_правка_удаление_и_ошибки(self):
        з = knowledge.добавить("контрагент", "ООО Ромашка", "ромашка", "")
        with self.assertRaises(ValueError):
            knowledge.добавить("контрагент", "ооо ромашка")
        with self.assertRaises(ValueError):
            knowledge.добавить("плохой", "Что-то")
        self.assertEqual(knowledge.изменить(з["id"], "контрагент", "ООО Ромашка", "ромашка, ромашки", "оплата 10 дней")["сведения"], "оплата 10 дней")
        self.assertTrue(knowledge.удалить(з["id"]))
        self.assertIsNone(knowledge.изменить(з["id"], "контрагент", "X"))

    # --- 7. правки результатов
    def _поручение_с_результатом(self):
        м = missions.создать("Закупка фильтра", [{"агент": "снабженец", "описание": "Найти фильтр", "ожидание": "цена"},
                                              {"агент": "бухгалтер", "описание": "Согласовать", "ожидание": "счёт"}])
        ход = [{"агент": "снабженец", "состояние": "готово", "результат": "Фильтр VIC C-111 в наличии"}]
        missions._сохранить(м["id"], ход=ход, шаг=1, статус="остановлено", итог="")
        return м["id"]

    def test_правка_результата_сохраняется_и_агент_учится(self):
        номер = self._поручение_с_результатом()
        м = missions.исправить_результат(номер, 0, "Фильтр VIC C-111 в наличии, цена 850 руб., доставка завтра")
        self.assertEqual(м["ход"][0]["результат"], "Фильтр VIC C-111 в наличии, цена 850 руб., доставка завтра")
        self.assertTrue(м["ход"][0]["правлено"])
        ошибки = [з["текст"] for з in agents.заметки("снабженец") if з["вид"] == "ошибка"]
        self.assertTrue(any("переписал результат" in е and "850" in е for е in ошибки))
        self.assertTrue(any(ф["источник"] == "правка" and "850" in ф["текст"] for ф in knowledge.факты("снабженец")))
        self.assertEqual(knowledge.последние_правки("снабженец")[0]["до"], "Фильтр VIC C-111 в наличии")
        with learning._замок:
            события = learning._ожидают.get("снабженец", [])
        self.assertTrue(any(с["вид"] == "правка" and "850" in с["хозяин_исправил_на"] for с in события))

    def test_правка_без_изменений_и_пустая_отклоняются(self):
        номер = self._поручение_с_результатом()
        with self.assertRaises(missions.ОшибкаПоручения):
            missions.исправить_результат(номер, 0, "  ")
        with self.assertRaises(missions.ОшибкаПоручения):
            missions.исправить_результат(номер, 1, "что-то")        # у шага ещё нет результата
        missions.исправить_результат(номер, 0, "Фильтр VIC C-111 в наличии")
        self.assertEqual(knowledge.последние_правки("снабженец"), [])

    def test_правка_не_идёт_пока_поручение_выполняется(self):
        номер = self._поручение_с_результатом()
        missions._идут.add(номер)
        try:
            with self.assertRaises(missions.ОшибкаПоручения):
                missions.исправить_результат(номер, 0, "Другой текст")
        finally:
            missions._идут.discard(номер)


if __name__ == "__main__":
    unittest.main()
