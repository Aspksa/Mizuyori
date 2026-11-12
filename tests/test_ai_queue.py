import io
import threading
import time
import unittest
import urllib.error
import urllib.request

from mizuyori import ai


def http_ошибка(код, заголовки=None):
    import email.message
    з = email.message.Message()
    for к, v in (заголовки or {}).items():
        з[к] = v
    return urllib.error.HTTPError("https://x", код, "x", з, io.BytesIO('{"error":{"message":"лимит"}}'.encode()))


class Ответ:
    def __init__(self, текст=b'{"ok": true}'):
        self.текст = текст

    def read(self):
        return self.текст

    def __enter__(self):
        return self

    def __exit__(self, *а):
        pass


class ТестОчередиИИ(unittest.TestCase):
    def setUp(self):
        self.старое = urllib.request.urlopen
        self.пауза = list(ai.ПАУЗЫ_ПОВТОРА)
        ai.ПАУЗЫ_ПОВТОРА[:] = [0.01] * 5
        ai._пауза_до = 0.0
        ai._счётчики.update(повторов=0, пауз=0)
        ai.установить_приоритет("чат")

    def tearDown(self):
        urllib.request.urlopen = self.старое
        ai.ПАУЗЫ_ПОВТОРА[:] = self.пауза
        ai._пауза_до = 0.0

    def test_429_повторяется_и_успешно_заканчивается(self):
        ответы = [http_ошибка(429, {"Retry-After": "0.01"}), http_ошибка(503), Ответ()]

        def ложный(*а, **к):
            о = ответы.pop(0)
            if isinstance(о, Exception):
                raise о
            return о
        urllib.request.urlopen = ложный
        with ai._открыть("https://x", "k", "/chat/completions", {"a": 1}) as р:
            self.assertEqual(р.read(), b'{"ok": true}')
        self.assertEqual(ai._счётчики["повторов"], 2)

    def test_после_лимита_повторов_отдаёт_понятную_ошибку(self):
        def всегда(*а, **к):
            raise http_ошибка(429, {"Retry-After": "0.01"})
        urllib.request.urlopen = всегда
        with self.assertRaises(ai.ОшибкаИИ) as к:
            ai._открыть("https://x", "k", "/chat/completions", {"a": 1})
        self.assertEqual(к.exception.код, 429)
        self.assertIn("Слишком много", str(к.exception))

    def test_401_не_повторяется(self):
        вызовы = []

        def ложный(*а, **к):
            вызовы.append(1)
            raise http_ошибка(401)
        urllib.request.urlopen = ложный
        with self.assertRaises(ai.ОшибкаИИ):
            ai._открыть("https://x", "k", "/models")
        self.assertEqual(len(вызовы), 1)

    def test_фон_уступает_чату(self):
        порядок = []
        чат_идёт = threading.Event()
        отпустить = threading.Event()

        def ложный(запрос, **к):
            метка = threading.current_thread().name
            порядок.append(f"старт {метка}")
            if метка == "чат":
                чат_идёт.set()
                отпустить.wait(2)
            return Ответ()
        urllib.request.urlopen = ложный

        def чат():
            ai.установить_приоритет("чат")
            ai._открыть("https://x", "k", "/c", {})

        def фон():
            ai.установить_приоритет("фон")
            ai._открыть("https://x", "k", "/c", {})
            порядок.append("фон готов")
        т1 = threading.Thread(target=чат, name="чат")
        т2 = threading.Thread(target=фон, name="фон")
        т1.start()
        чат_идёт.wait(2)
        т2.start()
        time.sleep(0.3)
        self.assertNotIn("старт фон", порядок)          # пока чат в работе, фон ждёт
        отпустить.set()
        т1.join(3), т2.join(3)
        self.assertIn("фон готов", порядок)

    def test_общая_пауза_после_429(self):
        ai._поставить_паузу(0.3)
        начало = time.monotonic()
        urllib.request.urlopen = lambda *а, **к: Ответ()
        ai._открыть("https://x", "k", "/c", {})
        self.assertGreaterEqual(time.monotonic() - начало, 0.25)


if __name__ == "__main__":
    unittest.main()
