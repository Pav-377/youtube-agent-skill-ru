"""tools/review.py: the owner's table goes out and comes back without losing anything."""
import contextlib, csv, io, json, os, shutil, sys, tempfile, unittest

from helpers import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
import review  # noqa: E402


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.set_path = os.path.join(self.tmp, "hooks_ru.json")
        shutil.copy(review.SETS["hooks"], self.set_path)
        self.saved = dict(review.SETS)
        review.SETS["hooks"] = self.set_path
        self.csv = os.path.join(self.tmp, "review.csv")
        with contextlib.redirect_stdout(io.StringIO()):
            review.export("hooks", self.csv)

    def tearDown(self):
        review.SETS.clear()
        review.SETS.update(self.saved)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def table(self):
        with open(self.csv, encoding="utf-8-sig", newline="") as fh:
            return list(csv.reader(fh, delimiter=";"))

    def test_excel_friendly(self):
        with open(self.csv, "rb") as fh:
            self.assertTrue(fh.read().startswith(b"\xef\xbb\xbf"))
        t = self.table()
        self.assertEqual(t[0], review.COLUMNS)
        with open(self.set_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(len(t) - 1, len(doc["hooks"]) + len(doc["pairs"]))
        disputed = sum(h["disputed"] for h in doc["hooks"])
        self.assertTrue(all(r[3].startswith("СПОРНО") for r in t[1:1 + disputed]))
        self.assertFalse(any(r[3].startswith("СПОРНО") for r in t[1 + disputed:]))

    def test_owner_edits_come_back_even_from_cp1251(self):
        t = self.table()
        target = next(r for r in t[1:] if r[2] == "сильный")
        target[4] = "Слабый"
        pair = next(r for r in t[1:] if r[0].startswith("p"))
        pair[4] = "перевод неточный"
        out = io.StringIO()
        csv.writer(out, delimiter=";", lineterminator="\r\n").writerows(t)
        with open(self.csv, "w", encoding="cp1251", newline="") as fh:  # as Excel may save it
            fh.write(out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            review.import_("hooks", self.csv)
        with open(self.set_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        hook = next(h for h in doc["hooks"] if h["id"] == target[0])
        self.assertEqual(hook["label"], "weak")
        self.assertTrue(hook["owner_changed"])
        self.assertEqual(next(p for p in doc["pairs"] if p["id"] == pair[0])["owner_note"], "перевод неточный")
        self.assertTrue(doc["status"].startswith("reviewed by the owner: 1 label"))


if __name__ == "__main__":
    unittest.main()
