"""title.py in Russian (brief 5.4, P4) and the two-size thumbnail rule (decision C)."""
import unittest

from helpers import run_json, run_script


def lint(title, *extra):
    return run_json("yt-package/title.py", "--title", title, *extra)[0]


def keys(r, field="issues"):
    return [k for k, _ in r[field]]


class Russian(unittest.TestCase):
    def test_detected(self):
        self.assertEqual(lint("Как снимать ролики на телефон")["lang"], "ru")
        self.assertEqual(lint("Claude Code + MCP: гайд")["lang"], "ru")

    def test_length_in_characters(self):
        title = "Ж" * 61
        self.assertIn("length", keys(lint(title)))
        self.assertNotIn("length", keys(lint("Ж" * 60)))

    def test_repeat_by_word_form(self):
        r = lint("Монтаж ролика за 10 минут", "--thumb", "МОНТАЖА НЕ БУДЕТ")
        self.assertIn("duplicate", keys(r))
        r = lint("Как я монтирую ролики", "--thumb", "ЗА ЧАС")
        self.assertNotIn("duplicate", keys(r))

    def test_stop_words_are_not_a_repeat(self):
        r = lint("Монтаж в телефоне и на ноутбуке", "--thumb", "И В КИНО")
        self.assertNotIn("duplicate", keys(r))

    def test_front_load_on_cyrillic(self):
        self.assertNotIn("front-load", keys(lint("Как снимать ролики на телефон")))
        self.assertIn("front-load", keys(lint("Как я это сделал")))

    def test_caps(self):
        self.assertIn("shouting", keys(lint("ШОК ЭТО КОНЕЦ ВСЕГО")))
        self.assertNotIn("shouting", keys(lint("Монтаж БЕЗ ПРОГРАММ")))

    def test_vague_in_any_form(self):
        self.assertIn("vague", keys(lint("Невероятная обложка для канала")))
        self.assertIn("vague", keys(lint("Самые лучшие советы")))

    def test_numbers_as_digits_or_words(self):
        self.assertNotIn("no-number", keys(lint("Семь ошибок новичка")))
        self.assertNotIn("no-number", keys(lint("Монтаж за 10 минут")))
        self.assertIn("no-number", keys(lint("Ошибки новичка")))

    def test_clickbait(self):
        for title in ("ШОК! Вы не поверите, что сделал Claude", "Шокирующая правда о YouTube",
                      "Это конец канала", "Довёл зрителей до слёз", "Сенсация в мире монтажа"):
            with self.subTest(title):
                self.assertIn("clickbait", keys(lint(title)))
        for title in ("Шоколадный торт за 10 минут", "Конец монтажа: финальные титры", "Мегаполис ночью"):
            with self.subTest(title):
                self.assertNotIn("clickbait", keys(lint(title)))

    def test_report_in_russian(self):
        p = run_script("yt-package/title.py", "--title", "ШОК! Вы не поверите", "--thumb", "ЭТО КОНЕЦ")
        self.assertIn("кликбейт", p.stdout)
        self.assertIn("оценка", p.stdout)


class Thumbnail(unittest.TestCase):
    """Decision C: big text counts meaningful words only; the small caption is checked apart."""

    def test_big_text_bands(self):
        cases = [("БЕЗ МОНТАЖА И ПРОГРАММ", None),        # 2 meaningful words
                 ("ОДИН ДВА ТРИ", None),
                 ("ОДИН ДВА ТРИ ЧЕТЫРЕ", "hint"),
                 ("ОДИН ДВА ТРИ ЧЕТЫРЕ ПЯТЬ", "hint"),
                 ("ОДИН ДВА ТРИ ЧЕТЫРЕ ПЯТЬ ШЕСТЬ", "issue"),
                 ("STOP POSTING EVERY DAY", "hint"),
                 ("THE CLIFF IS REAL", None)]               # the, is do not count
        for thumb, want in cases:
            with self.subTest(thumb):
                r = lint("Монтаж ролика за 10 минут", "--thumb", thumb)
                self.assertEqual("thumb-length" in keys(r, "hints"), want == "hint")
                self.assertEqual("thumb-length" in keys(r), want == "issue")

    def test_hint_does_not_cost_score(self):
        a = lint("Монтаж ролика за 10 минут", "--thumb", "ОДИН ДВА ТРИ")
        b = lint("Монтаж ролика за 10 минут", "--thumb", "ОДИН ДВА ТРИ ЧЕТЫРЕ")
        self.assertEqual(a["score"], b["score"])

    def test_small_caption_is_not_counted_in_the_big_text(self):
        r = lint("Монтаж ролика за 10 минут", "--thumb", "БЕЗ ПРОГРАММ",
                 "--thumb-small", "покажу каждый шаг на экране")
        self.assertEqual(keys(r) + keys(r, "hints"), [])

    def test_small_caption_limits(self):
        long_small = "раз два три четыре пять шесть семь"
        r = lint("Монтаж ролика за 10 минут", "--thumb", "БЕЗ ПРОГРАММ", "--thumb-small", long_small)
        self.assertIn("thumb-small", keys(r))
        r = lint("Монтаж ролика за 10 минут", "--thumb", "БЕЗ ПРОГРАММ", "--thumb-small", "весь монтаж за вечер")
        self.assertIn("thumb-small", keys(r))



class RussianWording(unittest.TestCase):
    def test_names_count_as_concrete(self):
        r = lint("Что сделал Claude с YouTube")
        self.assertNotIn("no-number", keys(r))
        self.assertIn("no-number", keys(lint("ШОК! КАК ЭТО ВОЗМОЖНО")))  # caps and sentence starts are not names

    def test_plural_forms(self):
        p = run_script("yt-package/title.py", "--title", "Монтаж ролика за 10 минут", "--thumb", "ОДИН ДВА ТРИ ЧЕТЫРЕ")
        self.assertIn("4 значимых слова", p.stdout)
        p = run_script("yt-package/title.py", "--title", "Монтаж за 21 минуту", "--thumb", "Х")
        self.assertIn("19 символов", p.stdout)


if __name__ == "__main__":
    unittest.main()
