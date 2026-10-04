"""Every script answers bad input with a sentence, never a traceback."""
import os, tempfile, unittest

from helpers import run_script

CASES = [
    ("yt-script/hookscore.py", ["--hook"]),
    ("yt-package/title.py", ["--title"]),
    ("yt-package/title.py", ["--title", "x", "--thumb"]),
    ("yt-package/title.py", ["--title", "x", "--thumb-small"]),
    ("yt-edit/deadair.py", ["{srt}", "--floor"]),
    ("yt-edit/deadair.py", ["{srt}", "--floor", "abc"]),
    ("yt-chapters/chapters.py", ["{srt}", "--target"]),
    ("yt-chapters/chapters.py", ["{srt}", "--target", "seven"]),
    ("yt-retention/retention.py", ["{csv}", "--duration"]),
    ("yt-retention/retention.py", ["{csv}", "--transcript"]),
    ("yt-viral/swipe.py", ["{json}", "--min"]),
    ("yt-script/aitells.py", ["--text"]),
    ("yt-script/aitells.py", ["--text", "x", "--long"]),
    ("yt-script/aitells.py", ["--text", "x", "--lang", "de"]),
    ("yt-edit/deadair.py", ["{srt}"]),
    ("yt-chapters/chapters.py", ["{srt}"]),
    ("yt-retention/retention.py", ["{csv}"]),
    ("yt-viral/swipe.py", ["{json}"]),
]


class NoTracebacks(unittest.TestCase):
    def test_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {}
            for ext, text in (("srt", ""), ("csv", ""), ("json", "[]")):
                files[ext] = os.path.join(tmp, "empty." + ext)
                with open(files[ext], "w", encoding="utf-8") as fh:
                    fh.write(text)
            for script, args in CASES:
                args = [a.format(**files) for a in args]
                with self.subTest(script=script, args=args):
                    p = run_script(script, *args)
                    self.assertNotIn("Traceback", p.stderr + p.stdout)




SCRIPTS = ["yt-script/hookscore.py", "yt-package/title.py", "yt-script/aitells.py", "yt-edit/deadair.py",
           "yt-chapters/chapters.py", "yt-retention/retention.py", "yt-viral/swipe.py"]


class MessagesFollowTheLocale(unittest.TestCase):
    """Help and "file not found" come before there is any text to detect a language from: they follow
    --lang, else the system locale. English stays as it always was."""

    def test_russian_locale(self):
        from helpers import LOCALE_RU
        for script in SCRIPTS:
            with self.subTest(script):
                out = run_script(script, "nofile.txt", env=LOCALE_RU).stdout
                self.assertIn("Файл не найден: nofile.txt", out)
                if "retention" not in script:  # retention.py answers with the one line only
                    self.assertIn("python3", out)
                self.assertNotIn("no such file", out)
                usage = run_script(script, env=LOCALE_RU).stdout
                self.assertRegex(usage, "[а-я]{4}")
                self.assertTrue(usage.startswith(os.path.basename(script) + " — "))

    def test_english_locale_prints_the_docstring(self):
        for script in SCRIPTS:
            with self.subTest(script):
                out = run_script(script, "nofile.txt").stdout
                self.assertNotIn("Файл не найден", out)
                self.assertTrue(out.startswith(os.path.basename(script) + " - ") or out.startswith("no such file"))

    def test_lang_flag_beats_the_locale(self):
        from helpers import LOCALE_RU
        out = run_script("yt-script/hookscore.py", "nofile.txt", "--lang", "en", env=LOCALE_RU).stdout
        self.assertTrue(out.startswith("hookscore.py - "))
        out = run_script("yt-retention/retention.py", "nofile.csv", "--lang", "ru").stdout
        self.assertIn("Файл не найден: nofile.csv", out)

    def test_no_cues_message(self):
        from helpers import LOCALE_RU
        with tempfile.TemporaryDirectory() as tmp:
            empty = os.path.join(tmp, "empty.srt")
            open(empty, "w", encoding="utf-8").close()
            self.assertIn("В файле нет реплик", run_script("yt-edit/deadair.py", empty, env=LOCALE_RU).stdout)
            self.assertIn("no cues found", run_script("yt-edit/deadair.py", empty).stdout)


class UiLang(unittest.TestCase):
    def setUp(self):
        import sys
        from helpers import SKILLS
        sys.path.insert(0, os.path.join(SKILLS, "yt-script"))
        import lang
        sys.path.pop(0)
        self.lang = lang

    def with_env(self, **env):
        from unittest import mock
        clean = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True):
            return self.lang.ui_lang()

    def test_environment(self):
        self.assertEqual(self.with_env(LANG="ru_RU.UTF-8"), "ru")
        self.assertEqual(self.with_env(LANG="en_US.UTF-8"), "en")
        self.assertEqual(self.with_env(LANG="C.UTF-8"), "en")
        self.assertEqual(self.with_env(LC_ALL="ru_RU.UTF-8", LANG="en_US.UTF-8"), "ru")
        self.assertEqual(self.with_env(LANG="", LANGUAGE="ru:en"), "ru")

    def test_flag_wins(self):
        self.assertEqual(self.lang.ui_lang("en"), "en")
        self.assertEqual(self.lang.ui_lang("ru"), "ru")


if __name__ == "__main__":
    unittest.main()
