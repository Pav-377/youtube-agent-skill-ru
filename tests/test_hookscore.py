"""hookscore.py in Russian: the mechanics (brief 5.2). Calibration against the reviewed set is separate."""
import os, sys, unittest

from helpers import SKILLS, run_json, run_script

sys.path.insert(0, os.path.join(SKILLS, "yt-script"))
import hookscore as hs  # noqa: E402
sys.path.pop(0)


def props(text):
    return hs.score(text, "ru")[0]


class Words(unittest.TestCase):
    def test_every_word_counts_and_punctuation_does_not(self):
        self.assertEqual(len(hs.ru_tokens("Claude только что уничтожил YouTube. Теперь — его!")), 7)


class Address(unittest.TestCase):
    def test_pronouns_in_any_form(self):
        for t in ("Это твой канал", "Тебе это знакомо", "Ваши ролики", "Для вас"):
            with self.subTest(t):
                self.assertGreater(props(t)["ADDRESS"], 26)

    def test_imperatives_and_second_person_verbs(self):
        for t in ("Смотри, что будет", "Не загружай ролик", "Теряешь зрителей на восьмой секунде", "Тратишь три часа"):
            with self.subTest(t):
                self.assertGreater(props(t)["ADDRESS"], 26)

    def test_no_false_address(self):
        for t in ("Я сам снял этот ролик", "Тишь да гладь", "Монтаж на телефоне", "В интернете пишут"):
            with self.subTest(t):
                self.assertEqual(props(t)["ADDRESS"], 26)

    def test_first_six_words_bonus(self):
        early = props("Ты теряешь зрителей")["ADDRESS"]
        late = props("Один два три четыре пять шесть семь ты")["ADDRESS"]
        self.assertEqual(early - late, 20 + 30)  # one more hit, plus the early bonus


class Specificity(unittest.TestCase):
    def test_numbers_as_digits_and_words(self):
        self.assertEqual(hs.ru_numbers("Пять тысяч просмотров за 30 дней"), 2)
        self.assertEqual(hs.ru_numbers("Без цифр вообще"), 0)

    def test_sentence_start_is_not_a_name(self):
        self.assertEqual(hs.ru_names("Теперь смотри. Claude помогает. Вот YouTube"), 1)  # YouTube only

    def test_vague_and_filler_cost(self):
        plain = props("Монтаж за час")["SPECIFICITY"]
        self.assertLess(props("Очень крутой монтаж за час")["SPECIFICITY"], plain)
        self.assertLess(props("Привет, друзья, монтаж за час")["SPECIFICITY"], plain)


class StakesAndCuriosity(unittest.TestCase):
    def test_stakes_by_stem(self):
        for t in ("Ты теряешь деньги", "Потерял канал", "Эта ошибка стоит времени", "Не трать вечер впустую"):
            with self.subTest(t):
                self.assertGreater(props(t)["STAKES"], 22 + 14)

    def test_curiosity_and_closed_answer(self):
        open_ = props("Почему никто не досматривает твои ролики?")["CURIOSITY"]
        self.assertGreater(open_, 24 + 18)
        closed = props("Никто не досматривает ролики, потому что начало скучное")["CURIOSITY"]
        self.assertLess(closed, props("Никто не досматривает ролики")["CURIOSITY"])


class Modes(unittest.TestCase):
    def test_language_is_detected_and_reported(self):
        r = run_json("yt-script/hookscore.py", "--hook", "Почему твои видео никто не досматривает?")[0]
        self.assertEqual(r["lang"], "ru")
        self.assertEqual(run_json("yt-script/hookscore.py", "--hook", "Why do your videos die?")[0]["lang"], "en")

    def test_lang_flag_forces_english(self):
        r = run_json("yt-script/hookscore.py", "--hook", "Почему твои видео никто не досматривает?", "--lang", "en")[0]
        self.assertEqual(r["lang"], "en")

    def test_russian_report(self):
        p = run_script("yt-script/hookscore.py", "--hook", "Почему твои видео никто не досматривает?")
        for word in ("КОНКРЕТИКА", "ОБРАЩЕНИЕ", "ИТОГ", "слабое место"):
            self.assertIn(word, p.stdout)


if __name__ == "__main__":
    unittest.main()
