"""deadair.py in Russian: hesitations, filler words in context, stumbles."""
import json, os, sys, unittest

from helpers import ROOT, SKILLS, fixture, run_json, run_script

sys.path.insert(0, os.path.join(SKILLS, "yt-edit"))
from fillers_ru import analyse  # noqa: E402
from transcript import Word  # noqa: E402
sys.path.pop(0)


def words(text, start=0.0, step=0.3, pauses=()):
    """Timed words: one every `step` seconds, plus an extra second of silence before each index in
    `pauses`."""
    out, t = [], start
    for i, w in enumerate(text.split()):
        if i in pauses:
            t += 1.0
        out.append(Word(round(t, 3), round(t + step, 3), w))
        t += step
    return out


def marks(text, **kw):
    return [(m["text"], m["decision"]) for m in analyse(words(text, **kw))]


class MustNotTouch(unittest.TestCase):
    """A word that carries meaning gets no mark at all."""

    def test_meaningful_uses(self):
        for text in ("Открой вот этот файл и сохрани его", "Делай вот так и всё получится",
                     "Это тип данных для чисел", "А как бы ты поступил на моём месте",
                     "Файл лежит в общем доступе", "Если он молчит, значит что-то случилось",
                     "Это не значит, что ты не прав", "У меня это получается лучше всех",
                     "Это самое важное в монтаже", "Посыплю стружкой, типа снежок",
                     "Я реально пошёл и сделал", "Он говорит: ну всё, пока",
                     "Ну и что, зато я умею слушать", "Стал короче на минуту",
                     "Ролик станет короче на треть", "Сделай монтаж короче"):
            with self.subTest(text):
                self.assertEqual(marks(text), [])


class KeepLiveSpeech(unittest.TestCase):
    def test_connector_at_phrase_start_is_kept(self):
        self.assertEqual(marks("Ну, смотри, всё просто"), [("Ну,", "KEEP")])
        self.assertEqual(marks("Короче, суть такая: монтаж за час"), [("Короче,", "KEEP")])

    def test_intensifiers_are_never_cut(self):
        self.assertEqual(marks("Это прям очень удобно и на самом деле быстро"), [])


class Cut(unittest.TestCase):
    def test_hesitations_always_go(self):
        for h in ("э", "ээ", "эээ", "эм", "мм", "ммм", "м-м", "Э,", "Ээ..."):
            with self.subTest(h):
                self.assertEqual(marks(f"Сейчас {h} покажу"), [(h, "CUT")])

    def test_stack_of_fillers(self):
        got = marks("Ну короче типа сделал монтаж")
        self.assertEqual(got, [("Ну", "KEEP"), ("короче", "CUT"), ("типа", "CUT")])

    def test_filler_inside_a_phrase(self):
        self.assertEqual(marks("Я хотел как бы снять ролик"), [("как бы", "CUT")])
        self.assertEqual(marks("и этот человек, значит, выпускает видео"), [("значит,", "CUT")])

    def test_filler_alone_in_a_pause(self):
        self.assertEqual(marks("Сделали монтаж вот потом обложку", pauses=(2, 3)),
                         [("вот", "CUT")])

    def test_stumble_on_a_function_word(self):
        got = analyse(words("я я покажу как монтировать"))
        self.assertEqual([(m["kind"], m["text"]) for m in got], [("repeat", "я")])

    def test_emphatic_repeat_stays(self):
        self.assertEqual(analyse(words("ужас ужас ужас какой монтаж")), [])


class Script(unittest.TestCase):
    def test_srt_hesitation_restart_and_approximate_times(self):
        r = run_json("yt-edit/deadair.py", fixture("ru", "edit_ru.srt"))
        kinds = {(c["kind"], c["start"]) for c in r["cuts"]}
        self.assertIn(("HESITATION", 2.1), kinds)
        self.assertIn(("REPEAT", 3.9), kinds)
        self.assertFalse(r["exact_times"])
        self.assertTrue(all(c["approx"] for c in r["cuts"]))
        p = run_script("yt-edit/deadair.py", fixture("ru", "edit_ru.srt"))
        self.assertIn("≈", p.stdout)
        self.assertIn("автосубтитры YouTube", p.stdout)

    def test_youtube_captions_give_exact_times(self):
        r = run_json("yt-edit/deadair.py", fixture("ru", "auto_ru.vtt"))
        self.assertTrue(r["exact_times"])
        p = run_script("yt-edit/deadair.py", fixture("ru", "auto_ru.vtt"))
        self.assertNotIn("≈", p.stdout)

    def test_every_mark_has_times_class_decision_and_reason(self):
        for c in run_json("yt-edit/deadair.py", fixture("ru", "edit_ru.srt"))["cuts"]:
            self.assertLess(c["start"], c["end"])
            self.assertIn(c["kind"], ("DEAD", "HESITATION", "FILLER", "REPEAT"))
            self.assertIn(c["decision"], ("CUT", "KEEP"))
            self.assertTrue(c["why"])

    def test_english_is_untouched(self):
        r = run_json("yt-edit/deadair.py", fixture("en", "edit_en.srt"))
        self.assertNotIn("lang", r)


if __name__ == "__main__":
    unittest.main()
