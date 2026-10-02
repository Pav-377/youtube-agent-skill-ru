"""shared/transcript.py: SRT, VTT, YouTube automatic captions and whisper JSON (brief 5.3, N3)."""
import json, os, sys, tempfile, unittest

from helpers import ROOT, fixture

sys.path.insert(0, os.path.join(ROOT, "shared"))
from transcript import load, load_words  # noqa: E402


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


class YouTubeAutoCaptions(unittest.TestCase):
    def check(self, path):
        self.assertEqual([t for _, _, t in load(path)], ["ну короче смотри сегодня", "про монтаж роликов"])
        words, exact = load_words(path)
        self.assertTrue(exact)
        self.assertEqual([(w.start, w.text) for w in words],
                         [(0.16, "ну"), (0.4, "короче"), (0.88, "смотри"), (1.36, "сегодня"),
                          (2.879, "про"), (3.12, "монтаж"), (3.6, "роликов")])

    def test_as_youtube_writes_it(self):
        self.check(fixture("ru", "auto_ru.vtt"))

    def test_with_the_blank_lines_trimmed_by_an_editor(self):
        with open(fixture("ru", "auto_ru.vtt"), encoding="utf-8") as fh:
            trimmed = "\n".join(l.rstrip() for l in fh.read().split("\n"))
        with tempfile.TemporaryDirectory() as tmp:
            self.check(write(tmp, "a.vtt", trimmed))

    def test_last_word_does_not_swallow_the_pause(self):
        words, _ = load_words(fixture("ru", "auto_ru.vtt"))
        last = words[3]  # "сегодня", next line starts at 2.879
        self.assertEqual(last.text, "сегодня")
        self.assertAlmostEqual(last.end, 1.36 + 0.08 * 7, places=3)

    def test_untimed_new_line_is_kept_once(self):
        vtt = ("WEBVTT\n\n00:00:00.000 --> 00:00:02.000 align:start position:0%\n \n"
               "привет<00:00:00.500><c> всем</c>\n\n"
               "00:00:02.000 --> 00:00:04.000 align:start position:0%\nпривет всем\n[Музыка]\n\n"
               "00:00:04.000 --> 00:00:04.010 align:start position:0%\n[Музыка]\n \n")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([t for _, _, t in load(write(tmp, "m.vtt", vtt))], ["привет всем", "[Музыка]"])


class PlainCaptions(unittest.TestCase):
    def test_markup_and_entities(self):
        vtt = ("WEBVTT\n\nNOTE made by hand\n\nintro\n00:00:01.000 --> 00:00:03.000\n"
               "<v Аня><i>Это</i> Q&amp;A</v>\n\n2\n00:00:03.000 --> 00:00:04.000\n<b>Всё</b>\n")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load(write(tmp, "p.vtt", vtt)), [(1.0, 3.0, "Это Q&A"), (3.0, 4.0, "Всё")])

    def test_srt_words_are_estimated_by_characters(self):
        srt = "1\n00:00:10,000 --> 00:00:12,000\nаа бббббб в\n"
        with tempfile.TemporaryDirectory() as tmp:
            words, exact = load_words(write(tmp, "e.srt", srt))
        self.assertFalse(exact)
        # 11 characters over 2 seconds: "бббббб" starts after 3 characters, "в" after 10
        self.assertEqual([(w.start, w.text) for w in words], [(10.0, "аа"), (10.545, "бббббб"), (11.818, "в")])
        self.assertEqual(words[-1].end, 12.0)

    def test_english_srt_is_read_as_before(self):
        self.assertEqual(len(load(fixture("en", "edit_en.srt"))), 14)


class Whisper(unittest.TestCase):
    def test_word_timestamps_are_used(self):
        doc = {"segments": [{"start": 0.0, "end": 2.0, "text": " Ну вот",
                             "words": [{"word": " Ну", "start": 0.1, "end": 0.3},
                                       {"word": " вот", "start": 0.9, "end": 1.2}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            words, exact = load_words(write(tmp, "w.json", json.dumps(doc, ensure_ascii=False)))
        self.assertTrue(exact)
        self.assertEqual(words[1], (0.9, 1.2, "вот"))

    def test_segments_without_words_are_estimated(self):
        words, exact = load_words(fixture("en", "edit_en_whisper.json"))
        self.assertFalse(exact)
        self.assertEqual(words[0].text, "So")


if __name__ == "__main__":
    unittest.main()
