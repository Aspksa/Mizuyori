import unittest

from mizuyori import browser_fetch, page_snapshot, tools

ПРИМЕР = """<html><head><style>.x{}</style><script>var a=1</script></head><body>
<h1>Фильтр VIC C-111</h1><p>Воздушный фильтр для Hilux.</p>
<ul><li>Цена: 1 250 руб.</li><li>В наличии: Владивосток</li></ul>
<a href="https://shop.example/c111">Купить</a><button>В корзину</button>
<input placeholder="Поиск по каталогу"></body></html>"""


class ТестСнимкаСтраницы(unittest.TestCase):
    def test_html_в_структуру(self):
        т = page_snapshot.html_в_текст(ПРИМЕР)
        self.assertIn("# Фильтр VIC C-111", т)
        self.assertIn("- Цена: 1 250 руб.", т)
        self.assertIn("(https://shop.example/c111)", т)
        self.assertIn("[кнопка] В корзину", т)
        self.assertIn("[поле: Поиск по каталогу]", т)
        self.assertNotIn("var a", т)

    def test_выдержка_по_словам(self):
        т = page_snapshot.html_в_текст(ПРИМЕР)
        в = page_snapshot.выдержка(т, ["цена"])
        self.assertIn("1 250", в)
        self.assertNotIn("Поиск по каталогу", в)
        self.assertIn("не найдено", page_snapshot.выдержка(т, ["бетон"]))

    def test_закрытые_адреса(self):
        for а in ("http://localhost:8000/", "http://127.0.0.1/", "http://192.168.1.5/x", "file:///etc/passwd", "ftp://x.y/"):
            self.assertFalse(page_snapshot.адрес_допустим(а)[0], а)
        self.assertTrue(page_snapshot.адрес_допустим("https://8.8.8.8/")[0])

    def test_инструмент_страница(self):
        старое = page_snapshot.снимок
        page_snapshot.снимок = lambda а: page_snapshot.html_в_текст(ПРИМЕР)
        try:
            итог = tools.вызвать("страница", {"описание": "Найди цену на https://shop.example/c111", "агент": "снабженец"})
        finally:
            page_snapshot.снимок = старое
        self.assertIn("1 250", итог)
        with self.assertRaises(PermissionError):
            tools.вызвать("страница", {"описание": "https://x.y/", "агент": "кадровик"})
        with self.assertRaises(ValueError):
            tools.вызвать("страница", {"описание": "без адреса", "агент": "снабженец"})

    def test_снимок_без_браузера_идёт_обычным_скачиванием(self):
        from mizuyori import senses
        старое = senses._скачать
        senses._скачать = lambda а: ПРИМЕР
        browser_fetch.настроить("")
        try:
            self.assertIn("Фильтр", page_snapshot.снимок("https://8.8.8.8/x"))
        finally:
            senses._скачать = старое


if __name__ == "__main__":
    unittest.main()
