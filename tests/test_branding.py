"""Publishing under another name: branding.json + tools/rebrand.py, and nothing left behind.

Every check runs on a copy of the repository, so the working tree is never changed.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, unittest, zipfile

from helpers import ROOT

TOKEN = re.compile(r"\{\{(?:OWNER|REPO|REPO_URL|AUTHOR)\}\}")
SKIP_DIRS = {".git", "_private", "dist", "__pycache__"}
# Personal identifiers of the previous maintainer, stored as SHA-256 of the lower-case word so the
# test itself does not carry them. A word is a run of letters, digits and . _ @ -.
FORBIDDEN_WORDS = {
    "ab81340404b6526bb0ebeaf44d31b5f7bb2c499e377b62f8c60f297b3f118de7",
    "7e7b5739c67d2c7401fff9f7bdb9fea4b04f26dea29a0e914660d7d2c2e72bf4",
    "32ad381ed36ad72467e347e607bb56c412c03919f868d8b0f1bd14d06c509944",
    "7e294cbaab09f815822b632b346b2db809c28299906fb11e722af1247e1cb44a",
}
WORD = re.compile(r"[\w.@-]+")
# Development material that stays out of the public repository and the archives.
FORBIDDEN_PATHS = ("docs/REPORT.md", "demo/", "tools/research/", "internal/", "CLAUDE.md", ".claude/",
                   "HANDOVER.md", "TZ_")
ASSISTANT_MARKS = ("Co-Authored-By", "Generated with [Claude")


def copy_repo(dest):
    shutil.copytree(ROOT, dest, ignore=lambda d, names: [n for n in names if n in SKIP_DIRS])


def files(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            yield os.path.relpath(p, base).replace(os.sep, "/"), p


def readb(path):
    with open(path, "rb") as fh:
        return fh.read()


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def text_of(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def forbidden_words(text):
    return {w for w in (m.strip(".-") for m in WORD.findall(text.lower()))
            if hashlib.sha256(w.encode("utf-8")).hexdigest() in FORBIDDEN_WORDS}


def bad_path(rel):
    return any(rel == p or rel.startswith(p) or ("/" + p) in ("/" + rel) for p in FORBIDDEN_PATHS)


def rebrand(where, **values):
    path = os.path.join(where, "branding.json")
    with open(path, encoding="utf-8") as fh:
        b = json.load(fh)
    b.update(values)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(b, fh, ensure_ascii=False, indent=1)
    return subprocess.run([sys.executable, os.path.join(where, "tools", "rebrand.py")], cwd=where,
                          capture_output=True, text=True, encoding="utf-8")


class Repository(unittest.TestCase):
    def test_no_personal_identifiers(self):
        found = {rel for rel, p in files(ROOT) if forbidden_words(text_of(readb(p)))}
        self.assertEqual(found, set())

    def test_no_development_material(self):
        self.assertEqual([rel for rel, _ in files(ROOT) if bad_path(rel)], [])

    def test_no_assistant_marks(self):
        me = os.path.abspath(__file__)
        found = [rel for rel, p in files(ROOT) if os.path.abspath(p) != me
                 and any(m in text_of(readb(p)) for m in ASSISTANT_MARKS)]
        self.assertEqual(found, [])

    def test_placeholders_or_names_in_the_manifests(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            plugin = json.load(fh)
        self.assertTrue(plugin["repository"].startswith(("{{REPO_URL}}", "https://")))
        self.assertIn(plugin["author"]["name"], read_text(os.path.join(ROOT, "LICENSE")))


class Rebrand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.repo = os.path.join(cls.tmp, "repo")
        copy_repo(cls.repo)
        cls.first = rebrand(cls.repo, owner="test-owner", repo="yt-agent-test", author='Иван "Тест" Петров',
                            plugin="my-plugin", marketplace="my-market")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read(self, rel):
        with open(os.path.join(self.repo, rel), encoding="utf-8") as fh:
            return fh.read()

    def test_runs(self):
        self.assertEqual(self.first.returncode, 0, self.first.stdout + self.first.stderr)

    def test_no_placeholders_left(self):
        left = [rel for rel, p in files(self.repo) if not rel.startswith("tests/")
                and rel != "tools/rebrand.py" and TOKEN.search(text_of(readb(p)))]
        self.assertEqual(left, [])

    def test_values_in_place(self):
        plugin = json.loads(self.read(".claude-plugin/plugin.json"))
        market = json.loads(self.read(".claude-plugin/marketplace.json"))
        self.assertEqual(plugin["name"], "my-plugin")
        self.assertEqual(plugin["author"]["name"], 'Иван "Тест" Петров')
        self.assertEqual(plugin["repository"], "https://github.com/test-owner/yt-agent-test")
        self.assertEqual((market["name"], market["plugins"][0]["name"]), ("my-market", "my-plugin"))
        self.assertIn('Copyright (c) 2026 Иван "Тест" Петров', self.read("LICENSE"))
        self.assertIn("Copyright (c) 2026 Jake Schincariol", self.read("LICENSE"))
        self.assertIn("/plugin install my-plugin@my-market", self.read("README.md"))
        self.assertIn("/plugin marketplace add test-owner/yt-agent-test", self.read("README.md"))
        self.assertIn("https://github.com/test-owner/yt-agent-test", self.read("docs/DM_MESSAGE.md"))

    def test_repository_checks_pass(self):
        p = subprocess.run([sys.executable, os.path.join(self.repo, "tools", "check.py")], cwd=self.repo,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_dist_is_clean(self):
        dist = os.path.join(self.repo, "dist")
        zips = sorted(f for f in os.listdir(dist) if f.endswith(".zip"))
        self.assertEqual(len(zips), 12)
        self.assertIn("my-market.zip", zips)
        for z in zips:
            with zipfile.ZipFile(os.path.join(dist, z)) as zf:
                for name in zf.namelist():
                    with self.subTest(zip=z, name=name):
                        self.assertFalse(bad_path(name.split("/", 1)[-1]))
                        text = text_of(zf.read(name))
                        self.assertIsNone(TOKEN.search(text))
                        self.assertEqual(forbidden_words(text), set())

    def test_second_run_with_other_values(self):
        repo = os.path.join(self.tmp, "again")
        shutil.copytree(self.repo, repo)
        p = rebrand(repo, owner="other-owner", repo="other-repo", author="Other Name",
                    plugin="youtube-agent-ru", marketplace="youtube-agent-skill-ru")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        readme = read_text(os.path.join(repo, "README.md"))
        self.assertIn("other-owner/other-repo", readme)
        self.assertNotIn("test-owner", readme)
        self.assertNotIn("my-plugin", readme)
        self.assertIn("Other Name", read_text(os.path.join(repo, "LICENSE")))
        self.assertNotIn("Петров", read_text(os.path.join(repo, "LICENSE")))

    def test_empty_values_are_refused(self):
        repo = os.path.join(self.tmp, "empty")
        copy_repo(repo)
        p = rebrand(repo, owner="", repo="", author="")
        self.assertEqual(p.returncode, 1)
        self.assertIn("fill in 'owner'", p.stdout)
        self.assertTrue(TOKEN.search(read_text(os.path.join(repo, "README.md"))))


if __name__ == "__main__":
    unittest.main()
