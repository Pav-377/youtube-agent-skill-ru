"""swipe.py: view counts as people copy them (N7). The formula classifier is tested elsewhere (P6)."""
import json, os, sys, tempfile, unittest

from helpers import SKILLS, run_script

sys.path.insert(0, os.path.join(SKILLS, "yt-viral"))
import swipe  # noqa: E402
sys.path.pop(0)


class ViewsOf(unittest.TestCase):
    def test_readable(self):
        cases = {412000: 412000, 3.0: 3, "412,000": 412000, "412.000": 412000, "200 000": 200000,
                 "200 000": 200000, "200 000": 200000, "1 234 567": 1234567, "950": 950,
                 "1,2K": 1200, "1.2M": 1200000, "1,2к": 1200, "1,2 тыс.": 1200, "12 тыс. просмотров": 12000,
                 "3 млн": 3000000, "3 млн просмотров": 3000000, "1.5B": 1500000000, "2,5 млрд": 2500000000,
                 "12K views": 12000, None: 0, "": 0}
        for value, want in cases.items():
            with self.subTest(value=value):
                self.assertEqual(swipe.views_of(value), want)

    def test_unreadable(self):
        for value in ("много", "12 штук", "1,5", "1.2.3", True, "K"):
            with self.subTest(value=value):
                self.assertIsNone(swipe.views_of(value))


class BadRows(unittest.TestCase):
    def run_rows(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rows, fh, ensure_ascii=False)
            return run_script("yt-viral/swipe.py", path, "--min", "0", "--json")

    def test_bad_row_is_skipped_with_its_number(self):
        rows = [{"channel": "к", "title": f"Ролик {i}", "views": 1000 + i} for i in range(5)]
        rows.insert(2, {"channel": "к", "title": "Странный ролик", "views": "много"})
        p = self.run_rows(rows)
        self.assertEqual(p.returncode, 0)
        self.assertIn("Видео 3 (Странный ролик)", p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(len(out["outliers"]), 5)
        self.assertEqual(out["outliers"][0]["median"], 1002)  # the bad row is not in the median


if __name__ == "__main__":
    unittest.main()
