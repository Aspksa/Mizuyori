import tempfile
import unittest
import zipfile
from pathlib import Path

from mizuyori import archive, disk
from mizuyori.database import База


class Диск(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        корень = Path(self.t.name)
        self.база = База(корень / "t.db"); self.база.подготовить()
        self._п = (archive.ПАПКА, disk.ПАПКА_КОПИЙ)
        archive.ПАПКА = корень / "архив"
        disk.ПАПКА_КОПИЙ = корень / "копии"
        self.к = archive.создать_контрагента(self.база, {"название": "ООО Ромашка", "инн": "7701234567"})

    def tearDown(self):
        archive.ПАПКА, disk.ПАПКА_КОПИЙ = self._п
        self.t.cleanup()

    def _файл(self, текст="Договор поставки №5 от 01.03.2026. Неустойка 0,1% за каждый день просрочки.", имя="договор.txt"):
        return archive.принять_файл(self.база, None, имя, текст.encode(), контрагент_id=self.к["id"])

    def test_дубль_не_принимается(self):
        self._файл()
        with self.assertRaises(archive.ОшибкаАрхива):
            self._файл(имя="копия.txt")

    def test_корзина_и_восстановление(self):
        ф = self._файл()
        archive.удалить_файл(self.база, ф["id"])
        self.assertEqual(archive.дерево(self.база)["всего_файлов"], 0)
        self.assertEqual(len(archive.корзина(self.база)), 1)
        self.assertEqual(archive.искать(self.база, "неустойка"), [])
        with self.assertRaises(archive.ОшибкаАрхива):
            self._файл(имя="снова.txt")        # дубль того, что в корзине, — подсказка восстановить
        в = archive.восстановить_файл(self.база, ф["id"])
        self.assertIsNone(в["удалён"])
        self.assertTrue(в["на_диске"])
        self.assertEqual(archive.дерево(self.база)["всего_файлов"], 1)

    def test_корзина_насовсем_и_срок(self):
        ф = self._файл()
        archive.удалить_файл(self.база, ф["id"])
        self.assertEqual(archive.очистить_корзину(self.база), 0)        # свежее не трогаем
        with self.база.соединение() as с:
            с.execute("UPDATE раб_файлы SET удалён = datetime('now','localtime','-40 days')")
        self.assertEqual(archive.очистить_корзину(self.база), 1)
        self.assertEqual(archive.корзина(self.база), [])

    def test_версии(self):
        ф = self._файл()
        с_ = archive.новая_версия(self.база, None, ф["id"], "договор.txt", "Договор №5. Неустойка 0,5%.".encode())
        self.assertEqual(с_["версия"], 2)
        ст = archive.версии(self.база, ф["id"])
        self.assertEqual([в["версия"] for в in ст], [2, 1])
        with self.assertRaises(archive.ОшибкаАрхива):
            archive.новая_версия(self.база, None, ф["id"], "договор.txt", "Договор №5. Неустойка 0,5%.".encode())
        назад = archive.вернуть_версию(self.база, None, ф["id"], ст[1]["id"])
        self.assertEqual(назад["версия"], 3)
        self.assertIn("0,1%", archive.прочитать_для_агента(self.база, ф["id"]))

    def test_резервная_копия(self):
        self._файл()
        р = disk.резервная_копия(self.база)
        self.assertEqual(р["файлов"], 1)
        with zipfile.ZipFile(disk.путь_копии(р["имя"])) as з:
            self.assertIn("база.sqlite", з.namelist())
            self.assertTrue(any(н.startswith("архив/") for н in з.namelist()))
        self.assertFalse(disk.нужна_копия())

    def test_юрист_видит_договор_с_цитатой_а_бухгалтерия_акты(self):
        self._файл()
        блок, агент = archive.для_вопроса(self.база, "Что в договоре про неустойку?")
        self.assertEqual(агент, "юрист")
        self.assertIn("Выдержки", блок)
        self.assertIn("Неустойка", блок)
        self.assertEqual(archive.прочитать_для_агента(self.база, 1, "бухгалтер") != "", True)   # договор бухгалтеру тоже доступен
        акт = archive.принять_файл(self.база, None, "акт.txt", "Акт выполненных работ №7".encode(), контрагент_id=self.к["id"])
        self.assertEqual(archive.прочитать_для_агента(self.база, акт["id"], "юрист"), "")        # акт юристу не нужен

    def test_проверка_находит_лишнее(self):
        ф = self._файл()
        (archive.ПАПКА / "мусор.txt").write_text("x")
        (archive.ПАПКА / ф["путь"]).unlink()
        р = disk.проверка(self.база)
        self.assertEqual(len(р["пропали_с_диска"]), 1)
        self.assertIn("мусор.txt", р["лишние_файлы"])


if __name__ == "__main__":
    unittest.main()


class МассоваяЗагрузка(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        корень = Path(self.t.name)
        self.база = База(корень / "t.db"); self.база.подготовить()
        self._п = archive.ПАПКА
        archive.ПАПКА = корень / "архив"

    def tearDown(self):
        archive.ПАПКА = self._п
        self.t.cleanup()

    def test_контрагент_и_договор_создаются_сами(self):
        д = archive.принять_файл(self.база, None, "дог.txt", ("ДОГОВОР ПОСТАВКИ №5 от 01.03.2026\nАО «Примавтодор» и ООО «Ромашка», ИНН 2540123456, в лице директора. Сумма 100000 руб").encode())
        self.assertTrue(д["создан_контрагент"])
        self.assertTrue(д["создан_договор"])
        с = archive.принять_файл(self.база, None, "счёт.txt", "Счёт на оплату №12 от 05.03.2026 по договору №5. Поставщик ООО «Ромашка» ИНН 2540123456. Итого 50000 руб".encode())
        self.assertFalse(с["создан_контрагент"])
        self.assertEqual(с["договор_id"], д["договор_id"])
        self.assertEqual(len(archive.контрагенты(self.база)), 1)

    def test_мы_не_становимся_контрагентом_и_папка_подсказывает(self):
        ф = archive.принять_файл(self.база, None, "письмо.txt", "Письмо. АО «Примавтодор» просит прислать документы.".encode(), подсказка_папки="СеверШина")
        self.assertEqual(ф["контрагент"], "СеверШина")
        self.assertEqual([к["название"] for к in archive.контрагенты(self.база)], ["СеверШина"])

    def test_zip(self):
        import io, zipfile
        б = io.BytesIO()
        with zipfile.ZipFile(б, "w") as з:
            з.writestr("Ромашка/дог.txt", "ДОГОВОР №1 ООО «Ромашка» ИНН 2540123456")
            з.writestr("Ромашка/акт.txt", "Акт выполненных работ №2. ООО «Ромашка» ИНН 2540123456")
            з.writestr("Ромашка/дубль.txt", "ДОГОВОР №1 ООО «Ромашка» ИНН 2540123456")
            з.writestr("__MACOSX/x.txt", "мусор")
        р = archive.принять_архив(self.база, None, "a.zip", б.getvalue())
        self.assertEqual([х["ок"] for х in р], [True, True, False])
        self.assertEqual(len(archive.контрагенты(self.база)), 1)
        self.assertEqual(archive.дерево(self.база)["всего_файлов"], 2)


class КольцоПамяти(unittest.TestCase):
    def test_сводка_и_раздел(self):
        from mizuyori import memory_ring
        with tempfile.TemporaryDirectory() as t:
            б = База(Path(t) / "t.db"); б.подготовить()
            б.запомнить("Любит зелёный чай", None, "другое", 3)
            с = {х["ключ"]: х for х in memory_ring.сводка(б)}
            self.assertEqual(с["память"]["число"], 1)
            self.assertEqual(с["чат"]["число"], 0)
            р = memory_ring.раздел(б, "память", 10, "чай")
            self.assertEqual(len(р["записи"]), 1)
            self.assertIsNone(memory_ring.раздел(б, "нет", 10))
            self.assertEqual(р["записи"][0]["ключ"], f'п{р["записи"][0]["id"]}')

    def test_граф_знаний(self):
        from mizuyori import memory_ring
        with tempfile.TemporaryDirectory() as t:
            б = База(Path(t) / "t.db"); б.подготовить()
            with б.соединение() as с:
                с.execute("INSERT INTO сущности(id, имя, ключ, тип) VALUES (1, 'Цель', 'цель', 'цель'), (2, 'Причина', 'причина', 'другое')")
            б.связать(1, "потому что", 2)
            д = memory_ring.граф(б)
            self.assertEqual({х["ключ"] for х in д["сущности"]}, {"е1", "е2"})
            self.assertEqual(len(д["отношения"]), 1)
