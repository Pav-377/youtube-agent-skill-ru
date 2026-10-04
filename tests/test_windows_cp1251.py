"""A Russian Windows (cp1251), on any OS through tests/winsim.py.

Each case runs twice - on the original commit, where the problem must show (otherwise the
simulation proves nothing), and on this version, where it must not.
"""
import os, shutil, subprocess, sys, tempfile, unittest

from helpers import ROOT, SKILLS, fixture
from golden import golden

WINSIM = os.path.join(ROOT, "tests", "winsim.py")
MOJIBAKE = "РљР°Рє"  # "Как" written as UTF-8 and read back as cp1251


def winsim(skills_root, script, *args):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
    return subprocess.run([sys.executable, WINSIM, os.path.join(skills_root, script)] + list(args),
                          capture_output=True, env=env, cwd=ROOT)


def _has_original_ref():
    return shutil.which("git") and subprocess.run(
        ["git", "cat-file", "-e", golden.ORIGINAL_REF + "^{commit}"], cwd=ROOT, capture_output=True).returncode == 0


class RussianWindows(unittest.TestCase):
    """This version: output is UTF-8 (lang.setup_output), files are read as what they are."""

    def out(self, p):
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace")[-500:])
        return p.stdout.decode("utf-8")

    def test_utf8_titles_file(self):
        out = self.out(winsim(SKILLS, "yt-package/title.py", fixture("ru", "titles_ru.txt")))
        self.assertIn("Как снимать ролики на телефон", out)
        self.assertNotIn(MOJIBAKE, out)

    def test_utf8_hooks_file(self):
        out = self.out(winsim(SKILLS, "yt-script/hookscore.py", fixture("ru", "titles_ru.txt")))
        self.assertIn("Почему ваши ролики", out)

    def test_emoji_and_arrows_in_output(self):
        out = self.out(winsim(SKILLS, "yt-script/hookscore.py", "--hook", "Тест 🔥 → эмодзи — тире"))
        self.assertIn("Тест 🔥 → эмодзи", out)

    def test_utf8_json_input(self):
        out = self.out(winsim(SKILLS, "yt-viral/swipe.py", fixture("ru", "swipe_ru.json"), "--min", "0"))
        self.assertIn("Все говорят снимать каждый день", out)

    def test_transcript_and_csv(self):
        self.out(winsim(SKILLS, "yt-edit/deadair.py", fixture("ru", "edit_ru.srt")))
        self.out(winsim(SKILLS, "yt-chapters/chapters.py", fixture("ru", "chapters_ru_flat.srt")))


@unittest.skipUnless(_has_original_ref(), "original commit not in local git history")
class SimulationReproducesTheOriginalProblem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.orig = golden.extract_original(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_original_shows_mojibake(self):
        p = winsim(self.orig, "yt-package/title.py", fixture("ru", "titles_ru.txt"))
        self.assertIn(MOJIBAKE, p.stdout.decode("cp1251"))

    def test_original_crashes_on_emoji(self):
        p = winsim(self.orig, "yt-script/hookscore.py", "--hook", "Тест 🔥 эмодзи")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(b"UnicodeEncodeError", p.stderr)


if __name__ == "__main__":
    unittest.main()
