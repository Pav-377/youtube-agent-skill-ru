"""tools/build.py and tools/check.py: they pass on the repo, and each check catches what it claims to."""
import json, os, shutil, sys, tempfile, unittest, zipfile

from helpers import ROOT, run_script
from test_known_issues import SMOKE

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build, check  # noqa: E402


def make_tree(tmp, files):
    for path, text in files.items():
        full = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(text if isinstance(text, bytes) else text.encode("utf-8"))


class Patched:
    """Point check/build at a temporary tree for the duration of a with-block."""

    def __init__(self, root):
        self.root = root

    def __enter__(self):
        self.saved = (check.ROOT, check.SKILLS, build.ROOT, build.SHARED, build.SKILLS)
        check.ROOT = build.ROOT = self.root
        check.SKILLS = build.SKILLS = os.path.join(self.root, "skills")
        build.SHARED = os.path.join(self.root, "shared")
        return self

    def __exit__(self, *exc):
        check.ROOT, check.SKILLS, build.ROOT, build.SHARED, build.SKILLS = self.saved


GOOD_SKILL = "---\nname: yt-demo\ndescription: >-\n  Does a thing. Use when\n  asked.\n---\n\n# yt-demo\n"


class RepoIsClean(unittest.TestCase):
    def test_check_passes(self):
        p = run_script("../tools/check.py", cwd=ROOT)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_build_check_passes(self):
        p = run_script("../tools/build.py", "--check", cwd=ROOT)
        self.assertEqual(p.returncode, 0, p.stdout)


class FrontmatterRules(unittest.TestCase):
    def test_folded_description_is_joined(self):
        self.assertEqual(check.frontmatter(GOOD_SKILL),
                         {"name": "yt-demo", "description": "Does a thing. Use when asked."})

    def problems(self, skill_md, folder="yt-demo"):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, {f"skills/{folder}/SKILL.md": skill_md})
            with Patched(tmp):
                return check.check_frontmatter()

    def test_good(self):
        self.assertEqual(self.problems(GOOD_SKILL), [])

    def test_violations(self):
        cases = {
            "uppercase name": GOOD_SKILL.replace("name: yt-demo", "name: YT-Demo"),
            "reserved word": GOOD_SKILL.replace("name: yt-demo", "name: claude-demo"),
            "long description": GOOD_SKILL.replace("Does a thing.", "x" * 1100),
            "xml tag": GOOD_SKILL.replace("Does a thing.", "Does <b>a</b> thing."),
            "no frontmatter": "# yt-demo\n",
            "empty description": "---\nname: yt-demo\ndescription:\n---\n",
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertTrue(self.problems(text), label)

    def test_name_must_match_folder(self):
        self.assertTrue(self.problems(GOOD_SKILL, folder="yt-other"))


class OtherChecksCatchProblems(unittest.TestCase):
    def run_check(self, fn, files):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, files)
            with Patched(tmp):
                return fn()

    def test_contained(self):
        self.assertTrue(self.run_check(check.check_contained, {
            "skills/yt-demo/SKILL.md": GOOD_SKILL + "Run ../yt-x/tool.py\n"}))
        self.assertTrue(self.run_check(check.check_contained, {
            "skills/yt-demo/SKILL.md": GOOD_SKILL,
            "skills/yt-demo/t.py": "import os\np = os.path.join('a', '..', 'b')\n"}))

    def test_text(self):
        self.assertTrue(self.run_check(check.check_text, {"a.md": b"\xef\xbb\xbfhi"}))
        self.assertTrue(self.run_check(check.check_text, {"a.md": "привет".encode("cp1251")}))

    def test_imports(self):
        for src in ("import requests\n", "import urllib.request\n", "from http import client\n"):
            with self.subTest(src):
                self.assertTrue(self.run_check(check.check_imports, {
                    "skills/yt-demo/SKILL.md": GOOD_SKILL, "skills/yt-demo/t.py": src, "shared/x.txt": ""}))

    @unittest.skipIf(sys.version_info < (3, 10), "sys.stdlib_module_names (the list of standard modules) only exists from Python 3.10; the third-party import check runs there")
    def test_imports_third_party(self):
        self.assertTrue(self.run_check(check.check_imports, {
            "skills/yt-demo/SKILL.md": GOOD_SKILL, "skills/yt-demo/t.py": "import numpy\n", "shared/x.txt": ""}))

    def test_links(self):
        self.assertTrue(self.run_check(check.check_links, {"README.md": "see [x](docs/missing.md)\n"}))
        self.assertEqual(self.run_check(check.check_links, {
            "README.md": "[x](docs/a.md#part) [y](https://e.com) [z](#top)\n", "docs/a.md": "a"}), [])

    def test_plugin_names_must_agree(self):
        files = {".claude-plugin/plugin.json": json.dumps({"name": "a"}),
                 ".claude-plugin/marketplace.json": json.dumps(
                     {"name": "m", "owner": {"name": "o"}, "plugins": [{"name": "b", "source": "./"}]})}
        self.assertTrue(self.run_check(check.check_plugin, files))

    def test_sync_detects_drift(self):
        files = {"shared/manifest.json": json.dumps({"files": {"x.py": ["yt-demo"]}}),
                 "shared/x.py": "a = 1\n", "skills/yt-demo/SKILL.md": GOOD_SKILL, "skills/yt-demo/x.py": "a = 2\n"}
        self.assertTrue(self.run_check(check.check_sync, files))


class Dist(unittest.TestCase):
    """Brief 6.2: every zip, unpacked alone into an empty folder, runs its scripts."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.zips = build.dist(os.path.join(cls.tmp, "a"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_twelve_archives(self):
        self.assertEqual(len(self.zips), 12)

    def test_deterministic(self):
        again = build.dist(os.path.join(self.tmp, "b"))
        for a, b in zip(self.zips, again):
            with open(a, "rb") as fa, open(b, "rb") as fb:
                self.assertEqual(fa.read(), fb.read(), os.path.basename(a))

    def test_each_skill_zip_runs_alone(self):
        for z in self.zips:
            name = os.path.splitext(os.path.basename(z))[0]
            if not name.startswith("yt-"):
                continue
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                zipfile.ZipFile(z).extractall(tmp)
                self.assertEqual(os.listdir(tmp), [name], "the skill folder must be the zip's only top level")
                self.assertTrue(os.path.isfile(os.path.join(tmp, name, "SKILL.md")))
                for script in sorted(os.listdir(os.path.join(tmp, name))):
                    if script in SMOKE:
                        p = run_script(script, *SMOKE[script], skills_root=os.path.join(tmp, name), cwd=tmp)
                        self.assertEqual(p.returncode, 0, f"{name}/{script}: {p.stderr[-400:]}")

    def test_plugin_zip_has_manifest(self):
        names = zipfile.ZipFile(self.zips[-1]).namelist()
        self.assertIn(f"{build.PLUGIN_NAME}/.claude-plugin/plugin.json", names)
        self.assertFalse([n for n in names if "__pycache__" in n or "_private" in n])



class SkillsCheckCatchesProblems(unittest.TestCase):
    def run_check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, files)
            with Patched(tmp):
                return check.check_skills()

    def test_good(self):
        self.assertEqual(self.run_check({
            "skills/yt-demo/SKILL.md": GOOD_SKILL + "## Russian-language mode\nSee [examples_ru.md](examples_ru.md).\n"
                                       'python3 "${CLAUDE_SKILL_DIR}/x.py"\n',
            "skills/yt-demo/examples_ru.md": "x"}), [])

    def test_missing_section_examples_and_bare_command(self):
        problems = self.run_check({"skills/yt-demo/SKILL.md": GOOD_SKILL + "python3 x.py --json\n"})
        self.assertEqual(len(problems), 3, problems)


if __name__ == "__main__":
    unittest.main()
