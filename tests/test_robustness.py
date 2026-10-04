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


if __name__ == "__main__":
    unittest.main()
