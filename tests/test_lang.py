"""shared/lang.py."""
import io, os, subprocess, sys, tempfile, unittest

from helpers import ROOT

sys.path.insert(0, os.path.join(ROOT, "shared"))
import lang  # noqa: E402

# (expected, text). The thresholds in lang.json are set from these; see its detection_note.
DETECTION = [
    ("ru", "Claude только что уничтожил YouTube. Теперь его можно подключить к каналу, "
           "и он будет вести весь твой контент за тебя."),
    ("ru", "Claude vs ChatGPT: кто лучше"),
    ("ru", "YouTube Studio Analytics: удержание"),
    ("ru", "Claude Code + MCP: гайд"),
    ("ru", "ChatGPT, Claude, Gemini, Perplexity, Midjourney: обзор"),
    ("ru", "MCP server для YouTube за 5 минут"),
    ("ru", "Обзор iPhone 17 Pro Max"),
    ("ru", "ШОК! ЭТО КОНЕЦ"),
    ("ru", "промпт для claude code"),
    ("ru", "гайд по claude code и mcp"),
    ("ru", "делаю монтаж в davinci resolve и premiere"),
    ("ru", "Как я снял ролик на iPhone"),
    ("ru", "AI агенты: топ 5"),
    ("ru", "Ёлка — «тест»"),
    ("en", "Claude just destroyed YouTube. Now you can connect it to your channel and it will run "
           "all your content for you."),
    ("en", "My trip to Moscow (Москва) in 2026"),
    ("en", "How to say спасибо like a native speaker"),
    ("en", "Russian YouTube: why channels like Редакция grow"),
    ("en", "I Let AI Run My Channel for 30 Days"),
    ("en", "THE BEST CAMERA FOR YOUTUBE"),
    ("en", "what does привет mean"),
]


class Detection(unittest.TestCase):
    def test_cases(self):
        for want, text in DETECTION:
            with self.subTest(text):
                self.assertEqual(lang.detect(text), want)

    def test_margin_around_the_threshold(self):
        """The plain-word shares of the two languages must not touch the threshold."""
        th = lang.DATA["word_share_for_russian"]
        for want, text in DETECTION:
            plain = lang.plain_words(text)
            if not plain:
                continue
            share = sum(lang.is_cyrillic(w) for w in plain) / len(plain)
            with self.subTest(text):
                if want == "ru":
                    self.assertGreaterEqual(share, th + 0.09)
                else:
                    self.assertLessEqual(share, th - 0.09)

    def test_no_letters(self):
        self.assertEqual(lang.detect("12345 67"), "en")
        self.assertEqual(lang.detect("", default="ru"), "ru")
        self.assertIsNone(lang.cyrillic_share("123"))

    def test_lang_flag(self):
        self.assertEqual(lang.take_lang_flag(["a.srt", "--lang", "RU", "--json"]), ("ru", ["a.srt", "--json"]))
        self.assertEqual(lang.take_lang_flag(["a.srt"]), ("auto", ["a.srt"]))
        with self.assertRaises(SystemExit):
            lang.take_lang_flag(["--lang", "de"])
        with self.assertRaises(SystemExit):
            lang.take_lang_flag(["--lang"])

    def test_resolve(self):
        self.assertEqual(lang.resolve("en", "привет мир"), "en")
        self.assertEqual(lang.resolve("auto", "привет мир"), "ru")


class Tokens(unittest.TestCase):
    def test_cyrillic_hyphens_apostrophes_numbers(self):
        self.assertEqual(lang.tokens("Какой-то ролик: слова-паразиты, don't, 3.5% и 80,5 — ок"),
                         ["Какой-то", "ролик", "слова-паразиты", "don't", "3.5%", "и", "80,5", "ок"])

    def test_typographic_apostrophe_and_spaces(self):
        self.assertEqual(lang.tokens("don’t stop 200 000"), ["don’t", "stop", "200", "000"])

    def test_case_and_yo_are_kept_for_output(self):
        self.assertEqual(lang.tokens("Ёлка"), ["Ёлка"])

    def test_dash_alone_is_not_a_word(self):
        self.assertEqual(lang.tokens("раз — два - три"), ["раз", "два", "три"])

    def test_words_drop_numbers_and_normalise(self):
        self.assertEqual(lang.words("Ещё 5 ЁЖИКОВ"), ["еще", "ежиков"])

    def test_p1_phrase_has_all_its_words(self):
        self.assertEqual(len(lang.tokens(DETECTION[0][1])), 20)


class Normalize(unittest.TestCase):
    def test_comparison_form(self):
        self.assertEqual(lang.normalize("Ёлка — «Тест»  “x” ’"), 'елка - "тест" "x" \'')

    def test_yo_equals_ye(self):
        self.assertEqual(lang.normalize("ещё"), lang.normalize("еще"))


class Stem(unittest.TestCase):
    # Reference pairs from the Snowball Russian sample vocabulary.
    SNOWBALL = {
        "вагон": "вагон", "вагона": "вагон", "вагоне": "вагон", "вагонов": "вагон", "вагоном": "вагон",
        "вагоны": "вагон", "важная": "важн", "важнее": "важн", "важнейшие": "важн", "важнейшими": "важн",
        "важничал": "важнича", "важно": "важн", "важного": "важн", "важное": "важн", "важной": "важн",
        "важном": "важн", "важному": "важн", "важную": "важн", "важные": "важн", "важным": "важн",
        "важными": "важн", "важных": "важн", "в": "в",
    }

    def test_snowball_reference(self):
        for word, want in self.SNOWBALL.items():
            with self.subTest(word):
                self.assertEqual(lang.stem(word), want)

    def test_official_snowball_sample(self):
        """400 pairs from the official Snowball test vocabulary (tests/fixtures/snowball_ru, BSD-3).
        The full 49785-word vocabulary matches 100%: tools/snowball_check.py."""
        path = os.path.join(ROOT, "tests", "fixtures", "snowball_ru", "sample.tsv")
        with open(path, encoding="utf-8") as fh:
            pairs = [line.rstrip("\n").split("\t") for line in fh if not line.startswith("#")]
        self.assertEqual(len(pairs), 400)
        self.assertEqual([(w, s, lang.stem(w)) for w, s in pairs if lang.stem(w) != s], [])

    def test_snowball_quirks_are_known(self):
        """Plain Snowball behaviour, kept: same_word() is what callers use to compare."""
        self.assertEqual(lang.stem("канал"), "кана")
        self.assertEqual(lang.stem("ошибок"), "ошибок")

    def test_forms_of_one_word_meet(self):
        groups = [["монтаж", "монтажа", "монтажу", "монтажом", "МОНТАЖА"],
                  ["ролик", "ролики", "роликов", "роликами"],
                  ["подписчик", "подписчики", "подписчиков"],
                  ["обложка", "обложки", "обложку", "обложкой", "обложек"],
                  ["канал", "канала", "каналу", "каналов"],
                  ["ошибка", "ошибки", "ошибок"],
                  ["слова-паразиты", "слово-паразит"],
                  ["ещё", "еще"]]
        for g in groups:
            for a in g:
                for b in g:
                    with self.subTest(a=a, b=b):
                        self.assertTrue(lang.same_word(a, b))

    def test_different_words_stay_apart(self):
        for a, b in [("монтаж", "монета"), ("канал", "кино"), ("свет", "звук"), ("ролик", "роль"),
                     ("звук", "звукорежиссер"), ("кот", "код"), ("ролик", "рол"), ("YouTube", "Tube"),
                     ("подписчик", "подписка"), ("слова-паразиты", "слова")]:
            with self.subTest(a=a, b=b):
                self.assertFalse(lang.same_word(a, b))

    def test_known_lookalike(self):
        """Documented limit of the prefix rule (see same_word): канал and канат meet."""
        self.assertTrue(lang.same_word("канал", "канат"))

    def test_short_words_survive(self):
        for w in ("я", "ты", "он", "на", "по", "ну", "вот"):
            with self.subTest(w):
                self.assertTrue(lang.stem(w))

    def test_latin_and_hyphen(self):
        self.assertEqual(lang.stem("YouTube"), "youtube")
        self.assertEqual(lang.stem("ещё"), lang.stem("еще"))


class ReadText(unittest.TestCase):
    TEXT = "Позиция,Удержание\n0,100\n"

    def read(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.csv")
            with open(path, "wb") as fh:
                fh.write(data)
            err = io.StringIO()
            saved, sys.stderr = sys.stderr, err
            try:
                return lang.read_text(path), err.getvalue()
            finally:
                sys.stderr = saved

    def test_encodings(self):
        for label, data in [("utf-8", self.TEXT.encode("utf-8")),
                            ("utf-8 bom", b"\xef\xbb\xbf" + self.TEXT.encode("utf-8")),
                            ("utf-16 le", self.TEXT.encode("utf-16")),
                            ("utf-16 be", b"\xfe\xff" + self.TEXT.encode("utf-16-be"))]:
            with self.subTest(label):
                text, err = self.read(data)
                self.assertEqual(text, self.TEXT)
                self.assertEqual(err, "")

    def test_cp1251_with_a_note_in_the_users_language(self):
        text, err = self.read(self.TEXT.encode("cp1251"))
        self.assertEqual(text, self.TEXT)
        self.assertIn("Windows-1251", err)
        self.assertIn("Файл f.csv", err)
        _, err_en = self.read(b"name,value\nWinter \xe9t\xe9,1\n")  # cp1252 bytes, not UTF-8
        self.assertIn("is not UTF-8", err_en)

    def test_read_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.json")
            with open(path, "wb") as fh:
                fh.write(b"\xef\xbb\xbf" + '{"a": "б"}'.encode("utf-8"))
            self.assertEqual(lang.read_json(path), {"a": "б"})


class Output(unittest.TestCase):
    SNIPPET = ("import sys; sys.path.insert(0, {shared!r}); import io, lang\n"
               "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='cp1251')\n"
               "lang.setup_output(); print('Тест 🔥 — ✓')")

    def run_snippet(self, env_extra):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
        env.update(env_extra)
        return subprocess.run([sys.executable, "-c", self.SNIPPET.format(shared=os.path.join(ROOT, "shared"))],
                              capture_output=True, env=env)

    def test_cp1251_pipe_becomes_utf8(self):
        p = self.run_snippet({})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.decode("utf-8").strip(), "Тест 🔥 — ✓")

    def test_users_own_encoding_is_respected_without_crashing(self):
        p = self.run_snippet({"PYTHONIOENCODING": "cp1251"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.decode("cp1251").strip(), "Тест ? — ?")



class NoResourceWarnings(unittest.TestCase):
    """The original left a ResourceWarning: transcripts were opened and never closed."""

    def test_scripts_close_their_files(self):
        from helpers import fixture, run_script
        from test_known_issues import SMOKE
        where = {"hookscore.py": "yt-script", "title.py": "yt-package", "deadair.py": "yt-edit",
                 "chapters.py": "yt-chapters", "retention.py": "yt-retention", "swipe.py": "yt-viral", "aitells.py": "yt-script"}
        extra = {"hookscore.py", "title.py"}
        for script, args in SMOKE.items():
            with self.subTest(script):
                if script in extra:  # also read a file, not only an argument
                    args = [fixture("ru", "titles_ru.txt")]
                p = run_script(f"{where[script]}/{script}", *args,
                               env={"PYTHONWARNINGS": "always::ResourceWarning"})
                self.assertEqual(p.returncode, 0, p.stderr[-300:])
                self.assertNotIn("ResourceWarning", p.stderr)


if __name__ == "__main__":
    unittest.main()
