"""aitells.py - machine-written stamps in a script."""
import json, os, sys, unittest

from helpers import SKILLS, fixture, run_json, run_script

sys.path.insert(0, os.path.join(SKILLS, "yt-script"))
import aitells  # noqa: E402
sys.path.pop(0)

with open(fixture("aitells_stamps.json"), encoding="utf-8") as fh:
    STAMPS = json.load(fh)


def recall(items, code):
    return sum(any(f["type"] == it["type"] for f in aitells.check(it["text"], code)) for it in items) / len(items)


class Acceptance(unittest.TestCase):
    def test_stamped_sentences_are_found(self):
        """At least 80% of sentences with deliberate stamps are found."""
        self.assertGreaterEqual(len(STAMPS["ru"]), 50)
        self.assertGreaterEqual(recall(STAMPS["ru"], "ru"), 0.80)
        self.assertGreaterEqual(recall(STAMPS["ru_heldout"], "ru"), 0.80)
        self.assertGreaterEqual(recall(STAMPS["en"], "en"), 0.80)


class Rules(unittest.TestCase):
    def types(self, text, code="ru"):
        return {f["type"] for f in aitells.check(text, code)}

    def test_each_kind(self):
        cases = {"contrast": "Это не про деньги, а про свободу.",
                 "canned": "Стоит отметить, что это бесплатно.",
                 "lead_in": "Знаешь, почему так происходит?",
                 "aphorism": "Голова — его, руки — твои.",
                 "triad": "Нужны идеи, время и силы. И ещё свет, звук и камера.",
                 "dashes": "Звук — это важно — и свет — тоже — и камера.",
                 "long": " ".join(["слово"] * 19) + "."}
        for kind, text in cases.items():
            with self.subTest(kind):
                self.assertIn(kind, self.types(text))

    def test_plain_speech_is_left_alone(self):
        for text in ("Я снимаю на телефон. Свет ставлю у окна. Монтирую вечером.",
                     "Вы все знаете, что такое ChatGPT.",
                     "Я не поехал, а остался дома.",
                     "Сейчас вы знаете, что там."):
            with self.subTest(text):
                self.assertFalse({f["type"] for f in aitells.check(text, "ru") if f["kind"] == "stamp"})

    def test_long_limit_is_configurable(self):
        text = " ".join(["слово"] * 20) + "."
        self.assertIn("long", self.types(text))
        p = run_script("yt-script/aitells.py", "--text", text, "--long", "25", "--json")
        self.assertNotIn("long", {f["type"] for f in json.loads(p.stdout)["findings"]})


class Script(unittest.TestCase):
    def test_finding_names_place_type_quote_and_hint(self):
        r = run_json("yt-script/aitells.py", "--text", "Привет.\n\nДавайте разберёмся, как это работает.")
        self.assertEqual(r["lang"], "ru")
        f = r["findings"][0]
        self.assertEqual((f["paragraph"], f["sentence"], f["type"], f["kind"]), (2, 1, "canned", "stamp"))
        self.assertTrue(f["quote"] and f["hint"])

    def test_report_in_russian_and_changes_nothing(self):
        p = run_script("yt-script/aitells.py", "--text", "Это не просто нейросеть, а помощник.")
        self.assertIn("штамп", p.stdout)
        self.assertIn("ничего не переписывает", p.stdout)

    def test_english(self):
        r = run_json("yt-script/aitells.py", "--text", "Let's dive in. It's worth noting that this is free.")
        self.assertEqual(r["lang"], "en")
        self.assertEqual({f["type"] for f in r["findings"]}, {"canned"})

    def test_copies_in_the_three_skills(self):
        for skill in ("yt-script", "yt-shorts", "yt-package"):
            with self.subTest(skill):
                self.assertTrue(os.path.exists(os.path.join(SKILLS, skill, "aitells.py")))


if __name__ == "__main__":
    unittest.main()
