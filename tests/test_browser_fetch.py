import unittest

from mizuyori import browser_fetch, config, senses


class БраузерДляПоиска(unittest.TestCase):
    def tearDown(self):
        browser_fetch.настроить("выкл")
        browser_fetch._сбой_до = 0.0

    def test_выключен_по_умолчанию(self):
        browser_fetch.настроить("выкл")
        self.assertFalse(browser_fetch.включён())
        self.assertIs(senses._получатель(), senses._скачать)

    def test_авто_включает_chrome_только_если_он_есть(self):
        старое = browser_fetch.авто_доступен
        try:
            browser_fetch.авто_доступен = lambda: True
            browser_fetch.настроить("авто")
            self.assertEqual(browser_fetch._режим, "chrome")
            browser_fetch.настроить("")
            self.assertEqual(browser_fetch._режим, "chrome")
            browser_fetch.авто_доступен = lambda: False
            browser_fetch.настроить("авто")
            self.assertEqual(browser_fetch._режим, "")
            browser_fetch.настроить("выкл")
            self.assertEqual(browser_fetch._режим, "")
        finally:
            browser_fetch.авто_доступен = старое

    def test_сбой_браузера_откатывается_на_обычное_и_откладывает_его(self):
        browser_fetch.настроить("chrome")
        старое = browser_fetch.скачать

        def упал(адрес, ожидание=40.0):
            raise RuntimeError("нет Chrome")
        browser_fetch.скачать = упал
        try:
            self.assertEqual(browser_fetch.с_откатом("https://x", lambda а: "обычное:" + а), "обычное:https://x")
            self.assertFalse(browser_fetch.включён())          # пауза после сбоя
        finally:
            browser_fetch.скачать = старое

    def test_работает_через_браузер_когда_включён(self):
        browser_fetch.настроить("chrome")
        старое = browser_fetch.скачать
        browser_fetch.скачать = lambda адрес, ожидание=40.0: "из браузера"
        try:
            self.assertEqual(senses._получатель()("https://x"), "из браузера")
        finally:
            browser_fetch.скачать = старое

    def test_настройка_проверяется(self):
        ок = lambda з: config.проверить_агентов({"браузер_для_поиска": з})["браузер_для_поиска"]
        self.assertEqual(ок("chrome"), "chrome")
        self.assertEqual(ок("http://127.0.0.1:9222/"), "http://127.0.0.1:9222")
        self.assertEqual(ок("http://evil.example:9222"), "авто")
        self.assertEqual(ок(5), "авто")
        self.assertEqual(ок("выкл"), "выкл")


if __name__ == "__main__":
    unittest.main()
