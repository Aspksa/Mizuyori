"""Модель эмбеддингов: если cloud.ru отвечает 404, программа берёт доступную модель, а не молча ломает «Мозги»."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mizuyori import ai, memory  # noqa: E402
from mizuyori.database import База  # noqa: E402

АДРЕС = "https://foundation-models.api.cloud.ru/v1"


class Ответ(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *а):
        return False


def сервер(модели, рабочие, вызовы=None, путь_есть=True):
    """Поддельный cloud.ru: /models отдаёт список, /embeddings работает только для моделей из «рабочие»."""
    def _открыть(адрес, ключ, путь, тело=None, таймаут=30):
        if вызовы is not None:
            вызовы.append((путь, (тело or {}).get("model")))
        if путь == "/models":
            return Ответ(json.dumps({"data": [{"id": м} for м in модели]}).encode())
        if путь == "/embeddings":
            if not путь_есть or тело["model"] not in рабочие:
                ош = ai.ОшибкаИИ("Не найдено: проверьте адрес API и название модели.")
                ош.код = 404
                raise ош
            return Ответ(json.dumps({"data": [{"index": i, "embedding": [1.0, float(i), 0.5]} for i, _ in enumerate(тело["input"])]}).encode())
        raise AssertionError(путь)
    return _открыть


class ЗаменаМодели(unittest.TestCase):
    def setUp(self):
        self.старое = ai._открыть
        ai._замены.clear()
        self.база = База(Path(tempfile.mkdtemp()) / "t.db")
        self.база.подготовить()
        self.н = {"адрес": АДРЕС, "ключ": "k", "модель_эмбеддингов": "Qwen/Qwen3-Embedding-0.6B"}

    def tearDown(self):
        ai._открыть = self.старое
        ai._замены.clear()

    def test_берём_доступную_модель_и_запоминаем(self):
        вызовы = []
        ai._открыть = сервер(["BAAI/bge-m3", "Qwen/Qwen3-32B", "BAAI/bge-reranker-v2-m3"], {"BAAI/bge-m3"}, вызовы)
        ключи, матрица, новых = memory.обеспечить_вектора(self.база, self.н, {"п1": "первый", "п2": "второй"})
        self.assertEqual((len(ключи), новых), (2, 2))
        self.assertEqual(ai.рабочая_модель_эмбеддингов(АДРЕС, "Qwen/Qwen3-Embedding-0.6B"), "BAAI/bge-m3")
        # вектора лежат под моделью, которая реально считала (а не под недоступной)
        self.assertEqual(len(self.база.вектора("BAAI/bge-m3")), 2)
        self.assertEqual(len(self.база.вектора("Qwen/Qwen3-Embedding-0.6B")), 0)
        # второй раз — сразу рабочая модель, без новой ошибки 404
        вызовы.clear()
        memory.обеспечить_вектора(self.база, self.н, {"п1": "первый", "п2": "второй", "п3": "третий"})
        self.assertNotIn(("/embeddings", "Qwen/Qwen3-Embedding-0.6B"), вызовы)

    def test_реранкер_не_берём_вместо_эмбеддингов(self):
        ai._открыть = сервер(["BAAI/bge-reranker-v2-m3", "Qwen/Qwen3-32B"], set())
        self.assertEqual(ai.модели_эмбеддингов(АДРЕС, "k"), [])
        with self.assertRaises(ai.ОшибкаИИ) as ош:
            memory.обеспечить_вектора(self.база, self.н, {"п1": "текст"})
        self.assertIn("нет среди доступных", str(ош.exception))

    def test_лучшая_модель_первой(self):
        ai._открыть = сервер(["intfloat/multilingual-e5-large", "BAAI/bge-m3", "Qwen/Qwen3-Embedding-0.6B"], set())
        self.assertEqual(ai.модели_эмбеддингов(АДРЕС, "k")[0], "BAAI/bge-m3")

    def test_модель_есть_а_адрес_не_найден(self):
        ai._открыть = сервер(["Qwen/Qwen3-Embedding-0.6B"], set())
        with self.assertRaises(ai.ОшибкаИИ) as ош:
            memory.обеспечить_вектора(self.база, self.н, {"п1": "текст"})
        self.assertIn("/v1", str(ош.exception))

    def test_запрос_тоже_переходит_на_замену(self):
        ai._открыть = сервер(["BAAI/bge-m3"], {"BAAI/bge-m3"})
        в = memory._вектор_запроса(self.н, "вопрос")
        self.assertEqual(len(в), 3)

    def test_другие_ошибки_не_маскируются(self):
        def ломается(адрес, ключ, путь, тело=None, таймаут=30):
            ош = ai.ОшибкаИИ("Ключ не подошёл")
            ош.код = 401
            raise ош
        ai._открыть = ломается
        with self.assertRaises(ai.ОшибкаИИ) as ош:
            memory.обеспечить_вектора(self.база, self.н, {"п1": "текст"})
        self.assertIn("Ключ не подошёл", str(ош.exception))


if __name__ == "__main__":
    unittest.main()
