"""Known problems of the original, written as the behaviour we want.

Each test is marked expectedFailure while the problem is open. When a fix lands, unittest reports an
"unexpected success" and the run fails - that is the signal to delete the decorator, so a fixed
problem can never silently regress. IDs match the brief (P1-P7) and the stage 0 audit (N1-N12).
"""
import ast, json, os, shutil, sys, tempfile, unittest

from helpers import FIXTURES, ROOT, SKILLS, fixture, run_json, run_script

P1_RU = ("Claude только что уничтожил YouTube. Теперь его можно подключить к каналу, "
         "и он будет вести весь твой контент за тебя.")
P1_EN = ("Claude just destroyed YouTube. Now you can connect it to your channel and it will run "
         "all your content for you.")


def hook(text):
    return run_json("yt-script/hookscore.py", "--hook", text)[0]


def load_cues(path):
    """The transcript loader, wherever it lives in this version of the tree."""
    sys.path.insert(0, os.path.join(SKILLS, "yt-edit"))
    try:
        try:
            from transcript import load
        except ImportError:
            from deadair import load
        return load(path)
    finally:
        sys.path.pop(0)


class P1_HookscoreRussian(unittest.TestCase):
    @unittest.expectedFailure
    def test_p1_phrase_scored_as_russian(self):
        ru, en = hook(P1_RU), hook(P1_EN)
        self.assertGreater(ru["properties"]["ADDRESS"], 26, "твой / тебя not seen as address")
        self.assertGreaterEqual(ru["properties"]["BREVITY"], 80, "20 words read as 3")
        self.assertLessEqual(abs(ru["verdict"] - en["verdict"]), 10)


class P2_RetentionDecimalComma(unittest.TestCase):
    """Fixed in stage 3."""

    def test_p2_decimal_comma(self):
        r = run_json("yt-retention/retention.py", fixture("ru", "retention_ru_comma.csv"))
        self.assertEqual(r["start"], 100.0)
        self.assertAlmostEqual(r["hook_leak"], 19.5)

    def test_p2_semicolon_separator(self):
        r = run_json("yt-retention/retention.py", fixture("ru", "retention_ru_semicolon.csv"))
        self.assertAlmostEqual(r["hook_leak"], 19.5)


class P3_DeadairRussian(unittest.TestCase):
    @unittest.expectedFailure
    def test_p3_hesitation_and_restart(self):
        cuts = run_json("yt-edit/deadair.py", fixture("ru", "edit_ru.srt"))["cuts"]
        kinds = {(c["kind"], c["start"]) for c in cuts}
        self.assertIn(("FILLER", 2.1), kinds, "«Эээ...» not cut")
        self.assertIn(("REPEAT", 3.9), kinds, "restart «Я покажу как я монтирую» not found")


class P4_TitleRussian(unittest.TestCase):
    """Fixed in stage 3."""

    def test_p4_duplicate_by_stem(self):
        r = run_json("yt-package/title.py", "--title", "Монтаж ролика за 10 минут",
                     "--thumb", "МОНТАЖА НЕ БУДЕТ")[0]
        self.assertIn("duplicate", [k for k, _ in r["issues"]])

    def test_n_title_front_load_false_positive(self):
        """Audit: every all-Cyrillic title was told its first three words are filler."""
        r = run_json("yt-package/title.py", "--title", "Как снимать ролики на телефон")[0]
        self.assertNotIn("front-load", [k for k, _ in r["issues"]])


class P5_ChaptersRussian(unittest.TestCase):
    @unittest.expectedFailure
    def test_p5_boundaries_from_vocabulary(self):
        r = run_json("yt-chapters/chapters.py", fixture("ru", "chapters_ru_flat.srt"), "--target", "4")
        starts = [c["start"] for c in r["chapters"]]
        for want, got in zip([0.0, 25.6, 51.2, 76.8], starts):
            self.assertLessEqual(abs(want - got), 3.3, starts)
        self.assertNotIn("Section", [c["draft_title"] for c in r["chapters"]])


class P6_SwipeRussian(unittest.TestCase):
    @unittest.expectedFailure
    def test_p6_formulas_on_russian_titles(self):
        with open(fixture("ru", "swipe_ru.json"), encoding="utf-8") as fh:
            want = {v["title"]: v["expected_formula"] for v in json.load(fh) if "expected_formula" in v}
        got = {r["title"]: r["formula"]
               for r in run_json("yt-viral/swipe.py", fixture("ru", "swipe_ru.json"), "--min", "0")["outliers"]}
        hits = sum(1 for t, f in want.items() if got.get(t) == f)
        self.assertGreaterEqual(hits, len(want) - 1, {t: got.get(t) for t in want})


# One runnable invocation per script, used by the isolation test. Paths are absolute fixtures.
SMOKE = {
    "hookscore.py": ["--hook", "Why do your videos die at 30 seconds?"],
    "title.py": ["--title", "I Let AI Run My Channel for 30 Days", "--thumb", "AI RAN IT"],
    "deadair.py": [fixture("en", "edit_en.srt")],
    "chapters.py": [fixture("en", "chapters_en.srt")],
    "retention.py": [fixture("en", "retention_en_seconds.csv"), "--transcript", fixture("en", "long_en.srt")],
    "swipe.py": [fixture("en", "swipe_en.json")],
}


class P7_SelfContainedSkills(unittest.TestCase):
    """Fixed in stage 1: shared/ + tools/build.py."""
    def test_p7_each_skill_runs_alone(self):
        failures = []
        for skill in sorted(os.listdir(SKILLS)):
            with tempfile.TemporaryDirectory() as tmp:
                dst = os.path.join(tmp, skill)
                shutil.copytree(os.path.join(SKILLS, skill), dst)
                for name in sorted(os.listdir(dst)):
                    if name in SMOKE:
                        p = run_script(name, *SMOKE[name], skills_root=dst, cwd=tmp)
                        if p.returncode != 0:
                            failures.append(f"{skill}/{name}: {p.stderr.strip().splitlines()[-1:]}")
        self.assertEqual(failures, [])

    def test_p7_skill_docs_stay_inside_their_folder(self):
        bad = []
        for skill in sorted(os.listdir(SKILLS)):
            with open(os.path.join(SKILLS, skill, "SKILL.md"), encoding="utf-8") as fh:
                if "../" in fh.read():
                    bad.append(skill)
        self.assertEqual(bad, [])

    def test_p7_skills_using_shared_tools_carry_them(self):
        need = {"yt-shorts": ["hookscore.py", "hooks.json"], "yt-audit": ["hookscore.py", "hooks.json", "title.py"],
                "yt-viral": ["hooks.json"]}
        missing = [f"{s}/{f}" for s, files in need.items() for f in files
                   if not os.path.exists(os.path.join(SKILLS, s, f))]
        self.assertEqual(missing, [])


class N_Encoding(unittest.TestCase):
    """Fixed in stage 2: shared/lang.py."""

    def test_n1_every_open_names_its_encoding(self):
        """On a Russian Windows open() defaults to cp1251 and UTF-8 input turns into mojibake."""
        bad = []
        for dirpath, _, files in os.walk(SKILLS):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                        mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
                        if "b" not in mode and "encoding" not in [k.arg for k in node.keywords]:
                            bad.append(f"{os.path.relpath(path, ROOT)}:{node.lineno}")
        self.assertEqual(bad, [])

    def test_n2_cp1251_console_does_not_crash(self):
        p = run_script("yt-script/hookscore.py", "--hook", "Тест 🔥 эмодзи и тире —",
                       env={"PYTHONIOENCODING": "cp1251"})
        self.assertEqual(p.returncode, 0, p.stderr[-300:])

    def test_n8_json_keeps_cyrillic_readable(self):
        p = run_script("yt-package/title.py", "--title", "Монтаж за 10 минут", "--json")
        self.assertIn("Монтаж", p.stdout)


class N_YouTubeAutoCaptions(unittest.TestCase):
    """Fixed in stage 3: shared/transcript.py."""

    def test_n3_tags_stripped_and_rolling_lines_merged(self):
        cues = load_cues(fixture("ru", "auto_ru.vtt"))
        text = " ".join(t for _, _, t in cues)
        self.assertNotIn("<", text)
        self.assertEqual(text.split(), "ну короче смотри сегодня про монтаж роликов".split())


class N_Retention(unittest.TestCase):
    """Fixed in stage 3."""

    def test_n4_transcript_on_percent_axis_without_duration(self):
        """--transcript used to print nothing at all when the axis is a percentage."""
        r = run_json("yt-retention/retention.py", fixture("en", "retention_en_pct.csv"),
                     "--transcript", fixture("en", "long_en.srt"))
        self.assertTrue(r["said"], "no transcript lines reported")

    def test_n5_short_video_on_seconds_axis(self):
        """A 60 s Short exported in seconds was read as a percentage axis (max x <= 100.5)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "short.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Video position (seconds),Audience retention (%)\n")
                y = 100.0
                for x in range(0, 61, 2):
                    y -= 6.0 if x == 44 else 0.5  # a cliff after the 30 s hook
                    fh.write(f"{x},{y:.1f}\n")
            r = run_json("yt-retention/retention.py", path)
        self.assertTrue(r["cliffs"])
        self.assertIsNotNone(r["cliffs"][0]["at_seconds"])

    def test_n6_cliff_reports_what_was_said_at_the_drop(self):
        """The drop between 190 s and 200 s is the sponsor read at 195-200 s."""
        r = run_json("yt-retention/retention.py", fixture("en", "retention_en_seconds.csv"),
                     "--transcript", fixture("en", "long_en.srt"))
        self.assertTrue(any("sponsor" in s for s in r["said"].values()), r["said"])

    def test_n6_hook_drop_is_not_listed_as_cliffs(self):
        r = run_json("yt-retention/retention.py", fixture("en", "retention_en_seconds.csv"))
        self.assertFalse([c for c in r["cliffs"] if c["at_seconds"] is not None and c["at_seconds"] < 30],
                         r["cliffs"])


class N_Swipe(unittest.TestCase):
    """Fixed in stage 3."""

    def test_n7_view_counts_as_text(self):
        views = ["1,2K", "1.2M", "1,2 тыс.", "3 млн", "200 000", "200 000"]
        want = [1200, 1200000, 1200, 3000000, 200000, 200000]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"channel": "c", "title": f"t{i}", "views": v} for i, v in enumerate(views)],
                          fh, ensure_ascii=False)
            r = run_json("yt-viral/swipe.py", path, "--min", "0")
        self.assertEqual(sorted(x["views"] for x in r["outliers"]), sorted(want))

    def test_n7_bad_view_count_is_a_message_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"channel": "c", "title": "t", "views": "много"}] * 4, fh, ensure_ascii=False)
            p = run_script("yt-viral/swipe.py", path)
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("много", p.stdout + p.stderr)


class N_Thumbnail(unittest.TestCase):
    """Fixed in stage 3."""

    def test_n9_thumb_small_repeating_the_title_is_flagged(self):
        """The small caption is checked on its own: here it repeats "videos" and "die" from the title."""
        r = run_json("yt-package/title.py", "--title", "Why Your Videos Die at 0:30", "--thumb", "THE CLIFF",
                     "--thumb-small", "your videos die here")[0]
        self.assertIn("thumb-small", json.dumps(r))

    def test_n9_four_meaningful_words_get_a_soft_hint(self):
        r = run_json("yt-package/title.py", "--title", "Posting schedule experiment",
                     "--thumb", "STOP POSTING EVERY DAY")[0]
        self.assertIn("thumb-length", json.dumps(r))


class N_HookscoreEnglishBugs(unittest.TestCase):
    """Decision B, option A: trailing period and ellipsis fixed in English; sentence start kept."""

    def test_n10_trailing_period_does_not_hide_filler(self):
        a = hook("Hey guys, welcome to my channel.")["properties"]["SPECIFICITY"]
        b = hook("Hey guys, welcome to my channel")["properties"]["SPECIFICITY"]
        self.assertEqual(a, b)

    def test_n10_sentence_start_quirk_is_kept_in_english(self):
        """Decision A: in English the first word of a second sentence still counts as a name.
        Fixing it made strong and weak hooks harder to tell apart. If this test fails, the quirk
        changed - re-run tools/hookeval.py and update CHANGELOG.md before accepting it."""
        a = hook("Now you can do it. Then you can rest.")["properties"]["SPECIFICITY"]
        b = hook("now you can do it. then you can rest.")["properties"]["SPECIFICITY"]
        self.assertEqual(a - b, 6)

    def test_n10_ellipsis_is_not_a_word(self):
        a = hook("Wait ... this changes how you edit")["properties"]["BREVITY"]
        b = hook("Wait this changes how you edit")["properties"]["BREVITY"]
        self.assertEqual(a, b)


class N_Chapters(unittest.TestCase):
    """Fixed in stage 1."""

    def test_n13_titles_do_not_depend_on_hash_seed(self):
        """Tied keywords were ordered by set iteration, so titles changed between runs."""
        outs = {run_script("yt-chapters/chapters.py", fixture("en", "chapters_en.srt"),
                           env={"PYTHONHASHSEED": str(seed)}).stdout for seed in range(6)}
        self.assertEqual(len(outs), 1)


class N_SkillDocs(unittest.TestCase):
    @unittest.expectedFailure
    def test_n12_yt_script_counts_its_tools_right(self):
        with open(os.path.join(SKILLS, "yt-script", "SKILL.md"), encoding="utf-8") as fh:
            self.assertNotIn("Two tools live in this folder", fh.read())


if __name__ == "__main__":
    unittest.main()
