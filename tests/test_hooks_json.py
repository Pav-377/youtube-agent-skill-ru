"""hooks.json: the Russian fields (brief 5.2)."""
import json, os, re, unittest

from helpers import ROOT

with open(os.path.join(ROOT, "shared", "hooks.json"), encoding="utf-8") as fh:
    DOC = json.load(fh)
HOOKS = DOC["hooks"]


class RussianFields(unittest.TestCase):
    def test_every_formula_has_them(self):
        self.assertEqual(len(HOOKS), 21)
        for h in HOOKS:
            with self.subTest(h["id"]):
                self.assertTrue(h["name_ru"] and h["shape_ru"])
                self.assertGreaterEqual(len(h["examples_ru"]), 2)
                self.assertLessEqual(len(h["examples_ru"]), 3)
                self.assertTrue(h["match_ru"])

    def test_english_fields_untouched(self):
        for h in HOOKS:
            self.assertEqual(set(h) - {"name_ru", "shape_ru", "examples_ru", "match_ru"},
                             {"id", "name", "shape", "example", "fails_when", "match"})

    def test_each_pattern_finds_its_own_and_not_three_others(self):
        """The brief: a Russian pattern matches at least one example of its formula and no example
        of at least three other formulas."""
        for h in HOOKS:
            for p in h["match_ru"]:
                with self.subTest(formula=h["id"], pattern=p):
                    rx = re.compile(p, re.I)
                    self.assertTrue(any(rx.search(e) for e in h["examples_ru"]), "matches none of its own")
                    clean = [o for o in HOOKS if o is not h and not any(rx.search(e) for e in o["examples_ru"])]
                    self.assertGreaterEqual(len(clean), 3)

    def test_examples_classify_as_their_formula(self):
        """Taken together, a formula's patterns should pick it for most of its own examples."""
        import sys
        sys.path.insert(0, os.path.join(ROOT, "skills", "yt-viral"))
        import swipe
        sys.path.pop(0)
        hits = total = 0
        for h in HOOKS:
            for e in h["examples_ru"]:
                total += 1
                hits += swipe.classify(e, "ru") == h["name_ru"]
        self.assertGreaterEqual(hits / total, 0.8, f"{hits}/{total}")
