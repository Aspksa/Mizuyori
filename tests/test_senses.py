"""Поиск в интернете для агентов: какие фразы понимаются и как работает запасной поисковик."""
import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mizuyori import senses  # noqa: E402


class РазборПросьбы(unittest.TestCase):
    def проверить(self, текст, запрос, агент=""):
        з, а = senses.разобрать_просьбу(текст)
        self.assertEqual((з, а), (запрос, агент), текст)

    def test_явные_глаголы(self):
        self.проверить("Снабженец, найди цену на шины", "цену на шины", "снабженец")
        self.проверить("Снабженец найди цену на шины", "цену на шины", "снабженец")  # без запятой
        self.проверить("найди поставщика шин во Владивостоке", "поставщика шин во Владивостоке")
        self.проверить("Снабженец, найди в интернете цену на масло 5W40", "цену на масло 5W40", "снабженец")
        self.проверить("Снабженец, загугли аккумулятор", "аккумулятор", "снабженец")

    def test_мягкие_глаголы_только_про_сеть_и_покупки(self):
        self.проверить("Снабженец, подбери аналоги тормозных колодок Хайлюкс", "аналоги тормозных колодок Хайлюкс", "снабженец")
        self.проверить("Снабженец, посмотри в интернете сколько стоит аккумулятор", "сколько стоит аккумулятор", "снабженец")
        self.проверить("Снабженец, сравни цены на аккумулятор", "цены на аккумулятор", "снабженец")
        # внутренние дела в интернет не уходят
        self.проверить("Снабженец, проверь договор с Автосервисом", "", "снабженец")
        self.проверить("Юрист, посмотри срок договора", "", "юрист")

    def test_снабженцу_можно_назвать_нужное(self):
        self.проверить("Снабженец, цены на шины Хайлюкс?", "цены на шины Хайлюкс", "снабженец")
        self.проверить("Снабженец, где купить масляный фильтр", "где купить масляный фильтр", "снабженец")
        self.проверить("Снабженец, какие цены у нас по договору с Автосервисом", "", "снабженец")  # про свои данные

    def test_обычные_фразы_не_ловятся(self):
        self.проверить("Что по ТО на Прадо?", "")
        self.проверить("Механик, что по ТО?", "")
        self.проверить("привет", "")


class УточнениеЗапроса(unittest.TestCase):
    def test_артикул_без_контекста_уточняется(self):
        self.assertEqual(senses.уточнить_запрос("фильтр vic c111", "снабженец"), "фильтр vic c111 автозапчасти артикул")
        self.assertEqual(senses.уточнить_запрос("фильтр C-111", "склад"), "фильтр C-111 автозапчасти артикул")

    def test_контекст_или_другой_агент_не_трогаем(self):
        self.assertEqual(senses.уточнить_запрос("масляный фильтр vic c111", "снабженец"), "масляный фильтр vic c111")
        self.assertEqual(senses.уточнить_запрос("фильтр для Toyota c111", "снабженец"), "фильтр для Toyota c111")
        self.assertEqual(senses.уточнить_запрос("фильтр vic c111", "юрист"), "фильтр vic c111")
        self.assertEqual(senses.уточнить_запрос("цены на шины", "снабженец"), "цены на шины")


class ПоискТехники(unittest.TestCase):
    def test_русская_с_в_артикуле(self):
        self.assertEqual(senses.исправить_раскладку_артикула("фильтр vic с111"), "фильтр vic c111")
        self.assertEqual(senses.исправить_раскладку_артикула("масло для двигателя"), "масло для двигателя")  # слова без цифр целы
        self.assertEqual(senses.ключ_артикула("C-111"), senses.ключ_артикула("с 111"))

    def test_фильтр_без_контекста_становится_автомобильным(self):
        self.assertEqual(senses.уточнить_запрос("фильтр", "снабженец"), "фильтр автомобильный")
        self.assertEqual(senses.уточнить_запрос("фильтр для воды", "снабженец"), "фильтр для воды")

    def test_несколько_запросов_для_запчасти(self):
        з = senses.построить_запросы("фильтр vic c111", "снабженец")
        self.assertGreaterEqual(len(з), 3)
        self.assertEqual(з[0], "фильтр vic c111 автозапчасти артикул")
        self.assertTrue(any("site:farpost.ru" in х for х in з))
        self.assertTrue(any("C-111" in х for х in з))                 # артикул с дефисом
        self.assertEqual(senses.построить_запросы("договор поставки", "юрист"), ["договор поставки"])
        канцелярия = senses.построить_запросы("канцелярия", "снабженец")
        self.assertEqual(len(канцелярия), 2)                                   # обычный + с Приморским краем
        self.assertIn("Владивосток Приморский край", канцелярия[1])
        self.assertTrue(any("4tochki.ru" in х for х in senses.построить_запросы("шины 265/65 R17", "снабженец")))

    def test_подсказки_модели_добавляются(self):
        з = senses.построить_запросы("масло 5W40", "снабженец", доп=["моторное масло 5W-40 синтетика"])
        self.assertIn("моторное масло 5W-40 синтетика", з)

    def test_цена_из_сниппета(self):
        self.assertEqual(senses.цена_из_текста("Фильтр VIC C-111 — от 1 250 руб. в наличии"), "1 250 ₽")
        self.assertEqual(senses.цена_из_текста("Цена 890 ₽"), "890 ₽")
        self.assertEqual(senses.цена_из_текста("без цены"), "")

    def test_магазин_с_артикулом_выше_википедии_и_воды(self):
        запрос = "фильтр vic c111 автозапчасти артикул"
        магазин = {"название": "VIC C-111 фильтр масляный", "ссылка": "https://www.exist.ru/x", "кратко": "от 450 руб."}
        вики = {"название": "Фильтр — Википедия", "ссылка": "https://ru.wikipedia.org/wiki/F", "кратко": "..."}
        вода = {"название": "Фильтры для воды", "ссылка": "https://aquaphor.ru/", "кратко": "очистка воды"}
        self.assertGreater(senses.оценить(магазин, запрос), senses.оценить(вики, запрос))
        self.assertGreater(senses.оценить(магазин, запрос), senses.оценить(вода, запрос))

    def test_склейка_без_повторов_и_порядок(self):
        def страница(*элементы):
            return "<ol>" + "".join(f'<li class="b_algo"><h2><a href="{u}">{n}</a></h2><p>{k}</p></li>' for u, n, k in элементы) + "</ol>"
        общий = страница(("https://ru.wikipedia.org/wiki/F", "Фильтр", "общее"), ("https://aquaphor.ru/", "Вода", "очистка воды"),
                         ("https://www.exist.ru/x", "VIC C-111", "от 450 руб."))
        магазины = страница(("https://www.exist.ru/x", "VIC C-111", "от 450 руб."), ("https://farpost.ru/y", "VIC C-111 Владивосток", "800 ₽"))

        def получить(адрес):
            if "duckduckgo" in адрес:
                return "<html></html>"
            return магазины if "site%3A" in адрес else общий
        р, использованные = senses.искать_для_закупки("фильтр vic c111", "снабженец", получить=получить)
        ссылки = [x["ссылка"] for x in р]
        self.assertEqual(len(ссылки), len(set(ссылки)))                         # без повторов
        self.assertIn("https://farpost.ru/y", ссылки)
        self.assertTrue(ссылки.index("https://www.exist.ru/x") < ссылки.index("https://ru.wikipedia.org/wiki/F"))
        self.assertGreaterEqual(len(использованные), 3)

    def test_в_чате_видны_цена_и_метка_магазина(self):
        from contextlib import contextmanager
        from mizuyori import agents
        старое = agents.работа, senses.искать_для_закупки

        @contextmanager
        def работа(*а, **к):
            yield {}
        agents.работа = работа
        senses.искать_для_закупки = lambda *а, **к: ([{"название": "VIC C-111", "ссылка": "https://www.exist.ru/x", "кратко": "от 1 250 руб."}], [])
        try:
            _, сообщение = senses.найти_для_чата("фильтр vic с111", "снабженец")
        finally:
            agents.работа, senses.искать_для_закупки = старое
        self.assertIn("**1 250 ₽**", сообщение)
        self.assertIn("магазин запчастей", сообщение)
        self.assertIn("vic c111", сообщение)                                    # раскладка исправлена в «искал»


class ПриоритетПриморья(unittest.TestCase):
    def test_региональный_запрос_только_снабжению_и_без_дубля(self):
        self.assertTrue(any("Владивосток Приморский край" in з for з in senses.построить_запросы("фильтр vic c111", "снабженец")))
        self.assertFalse(any("Приморский край" in з for з in senses.построить_запросы("срок договора", "юрист")))
        self.assertEqual(len([з for з in senses.построить_запросы("масло 5W40 во Владивостоке", "снабженец") if "Приморский край" in з]), 0)

    def test_местное_выше(self):
        запрос = "фильтр vic c111 автозапчасти артикул"
        местный = {"название": "VIC C-111 Владивосток", "ссылка": "https://farpost.ru/vladivostok/x", "кратко": "800 ₽"}
        дальний = {"название": "VIC C-111", "ссылка": "https://www.exist.ru/x", "кратко": "от 450 руб."}
        self.assertTrue(senses.из_приморья(местный))
        self.assertFalse(senses.из_приморья(дальний))
        self.assertGreater(senses.оценить(местный, запрос), senses.оценить(дальний, запрос))
        self.assertTrue(senses.из_приморья({"название": "Шины", "ссылка": "https://a.ru", "кратко": "самовывоз Уссурийск"}))

    def test_метка_в_ответе_чата(self):
        from contextlib import contextmanager
        from mizuyori import agents
        старое = agents.работа, senses.искать_для_закупки

        @contextmanager
        def работа(*а, **к):
            yield {}
        agents.работа = работа
        senses.искать_для_закупки = lambda *а, **к: ([{"название": "Фильтр", "ссылка": "https://farpost.ru/vladivostok/x", "кратко": "самовывоз"}], [])
        try:
            _, сообщение = senses.найти_для_чата("фильтр vic c111", "снабженец")
        finally:
            agents.работа, senses.искать_для_закупки = старое
        self.assertIn("📍 Приморье", сообщение)
        self.assertIn("Приоритет — Приморский край", сообщение)


ДДГ_КАПЧА = "<html><body>anomaly: please complete the captcha</body></html>"
БИНГ = ('<ol><li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&&p=1&u=a1' +
        base64.urlsafe_b64encode(b"https://shop.example/tires?a=1").decode().rstrip("=") +
        '&ntb=1">Шины <strong>Хайлюкс</strong> — магазин</a></h2><p>Цены от 5 000 руб.</p></li>'
        '<li class="b_algo"><h2><a href="https://other.example/">Другой</a></h2><p>Ещё</p></li></ol>')


class ЗапаснойПоисковик(unittest.TestCase):
    def setUp(self):
        senses._отказ_до.clear()

    def tearDown(self):
        senses._отказ_до.clear()

    def test_капча_запоминается_и_не_повторяется(self):
        вызовы = []

        def получить(адрес):
            вызовы.append(адрес)
            return ДДГ_КАПЧА if "duckduckgo" in адрес else БИНГ
        senses.искать("шины", получить=получить)
        вызовы.clear()
        senses.искать("масло", получить=получить)
        self.assertEqual(len(вызовы), 1)
        self.assertIn("bing", вызовы[0])

    def test_mojeek_последний_запасной(self):
        МОДЖИК = ('<ul><li><a class="ob" href="https://m.example/">m.example</a><h2><a class="title" href="https://m.example/p">Фильтр VIC C-111</a></h2>'
                  '<p class="s">Купить фильтр</p></li></ul>')

        def получить(адрес):
            if "mojeek" in адрес:
                return МОДЖИК
            return "<html></html>" if "bing" in адрес else ДДГ_КАПЧА
        р = senses.искать("vic c111", получить=получить)
        self.assertEqual(р[0]["ссылка"], "https://m.example/p")
        self.assertEqual(р[0]["название"], "Фильтр VIC C-111")

    def test_капча_duckduckgo_уходит_в_bing(self):
        вызовы = []

        def получить(адрес):
            вызовы.append(адрес)
            return ДДГ_КАПЧА if "duckduckgo" in адрес else БИНГ
        р = senses.искать("шины хайлюкс", получить=получить)
        self.assertEqual(len(вызовы), 2)
        self.assertEqual(р[0]["ссылка"], "https://shop.example/tires?a=1")   # redirect Bing раскрыт
        self.assertEqual(р[0]["название"], "Шины Хайлюкс — магазин")
        self.assertEqual(р[0]["кратко"], "Цены от 5 000 руб.")

    def test_если_ни_один_не_ответил_ошибка_сети(self):
        def получить(адрес):
            raise OSError("нет сети")
        with self.assertRaises(OSError):
            senses.искать("шины", получить=получить)

    def test_пустая_выдача_не_ошибка(self):
        self.assertEqual(senses.искать("абвгд", получить=lambda а: "<html></html>"), [])


class ЗапасноеЧерезКлюч(unittest.TestCase):
    """Нет сети (или пусто) → ответ из знаний модели по ключу, с честной оговоркой."""
    НАСТРОЙКИ = {"включён": True, "ключ": "k", "модель": "m", "адрес": "https://x"}

    def setUp(self):
        from mizuyori import agents, ai
        self.ai = ai
        self.agents = agents
        self.старое = (ai.справка_без_сети, agents.работа, senses.искать)
        ai.справка_без_сети = lambda запрос, н: "- Смотрите на размер и индекс нагрузки.\n- Аналоги: …"
        from contextlib import contextmanager

        @contextmanager
        def работа(*а, **к):
            yield {}
        agents.работа = работа

    def tearDown(self):
        self.ai.справка_без_сети, self.agents.работа, senses.искать = self.старое

    def test_нет_сети_и_есть_ключ(self):
        def нет_сети(*а, **к):
            raise OSError("нет сети")
        senses.искать = нет_сети
        _, сообщение = senses.найти_для_чата("шины хайлюкс", настройки_ии=self.НАСТРОЙКИ)
        self.assertIn("из знаний модели", сообщение)
        self.assertIn("не проверены", сообщение)
        self.assertIn("индекс нагрузки", сообщение)

    def test_нет_сети_и_нет_ключа(self):
        def нет_сети(*а, **к):
            raise OSError("нет сети")
        senses.искать = нет_сети
        _, сообщение = senses.найти_для_чата("шины хайлюкс", настройки_ии={})
        self.assertIn("Не смог выйти в интернет", сообщение)
        self.assertNotIn("индекс нагрузки", сообщение)

    def test_сеть_есть_ключ_не_нужен(self):
        senses.искать = lambda *а, **к: [{"название": "Магазин", "ссылка": "https://s.example", "кратко": "от 5000"}]
        _, сообщение = senses.найти_для_чата("шины", настройки_ии=self.НАСТРОЙКИ)
        self.assertIn("https://s.example", сообщение)
        self.assertNotIn("знаний модели", сообщение)

    def test_пусто_в_сети_уходит_к_модели(self):
        senses.искать = lambda *а, **к: []
        _, сообщение = senses.найти_для_чата("шины", настройки_ии=self.НАСТРОЙКИ)
        self.assertIn("ничего не нашлось", сообщение)
        self.assertIn("из знаний модели", сообщение)


if __name__ == "__main__":
    unittest.main()


class ТестКэшаИЦен(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from mizuyori import agents
        from mizuyori.database import База
        self.папка = tempfile.TemporaryDirectory()
        self.база = База(Path(self.папка.name) / "t.db")
        self.база.подготовить()
        agents.подключить(self.база)
        self.старое = senses._получатель

    def tearDown(self):
        senses._получатель = self.старое
        self.папка.cleanup()

    def test_выдача_кэшируется_на_часы(self):
        вызовы = []
        html_ = '<a class="result__a" href="https://shop.example/x">Фильтр</a>'
        senses._получатель = lambda: (lambda адрес: вызовы.append(адрес) or html_)
        движки = senses._порядок_поисковиков
        senses._порядок_поисковиков = lambda: [("тест", lambda з, п: [{"название": "Фильтр C-111", "ссылка": "https://shop.example/x", "кратко": ""}])]
        try:
            первая = senses.искать("фильтр vic c111")
            self.assertEqual(len(первая), 1)
            senses._порядок_поисковиков = lambda: [("тест", lambda з, п: (_ for _ in ()).throw(OSError("нет сети")))]
            вторая = senses.искать("Фильтр  VIC c111")        # регистр и пробелы не важны
            self.assertEqual(вторая, первая)
            with self.assertRaises(OSError):
                senses.искать("фильтр vic c111", кэш=False)
        finally:
            senses._порядок_поисковиков = движки

    def test_цена_рядом_с_артикулом(self):
        снимок = "Доставка от 300 руб.\n# Каталог\n- Фильтр VIC C-110\n- 900 руб.\n- Фильтр VIC C-111 воздушный\n- Цена 1 250 руб."
        self.assertEqual(senses.цена_со_страницы(снимок, "фильтр C111"), ("1 250 ₽", True))
        self.assertEqual(senses.цена_со_страницы("Товар за 500 руб.", "шины"), ("500 ₽", False))

    def test_цены_добавляются_магазинам_без_цены(self):
        результаты = [{"название": "Фильтр C-111", "ссылка": "https://exist.ru/p/1", "кратко": ""},
                      {"название": "Блог про фильтры", "ссылка": "https://blog.example/a", "кратко": ""},
                      {"название": "Уже с ценой", "ссылка": "https://emex.ru/p/2", "кратко": "1 000 руб."}]
        вызовы = []
        senses.добавить_цены(результаты, "фильтр C111", снимок=lambda а: вызовы.append(а) or "Фильтр VIC C-111\nЦена 1 250 руб.")
        self.assertEqual(результаты[0]["цена"], "1 250 ₽")
        self.assertTrue(результаты[0]["цена_точно"])
        self.assertNotIn("цена", результаты[1])
        self.assertEqual(вызовы, ["https://exist.ru/p/1"])
        senses.добавить_цены(результаты, "фильтр C111", снимок=lambda а: self.fail("должно быть из кэша"))
