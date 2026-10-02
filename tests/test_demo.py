"""demo/: the commands in demo/README.md print what demo/expected/ says (brief 6.5)."""
import os, shutil, subprocess, sys, unittest

from helpers import ROOT

DEMO = os.path.join(ROOT, "demo")
sys.path.insert(0, DEMO)
import make_demo_files as demo  # noqa: E402
sys.path.pop(0)


def expected(name):
    with open(os.path.join(DEMO, "expected", name), encoding="utf-8") as fh:  # universal newlines
        return fh.read()


class ThisVersion(unittest.TestCase):
    def test_every_case_matches(self):
        for name, script, args in demo.CASES:
            with self.subTest(name):
                self.assertEqual(demo.run(script, args).replace("\r\n", "\n"), expected(name))

    def test_the_claims_in_the_readme(self):
        self.assertIn("ИТОГ           38", expected("1_hook.txt"))
        self.assertIn("в начале ушли 19,5% зрителей", expected("3_retention.txt"))
        self.assertIn("Штампов: 6", expected("4_aitells.txt"))
        fillers = expected("2_fillers.txt")
        for keep in ("«Ну,»", "«В общем,»"):
            self.assertIn(keep, fillers)
        for meaningful in ("«Вот", "«значит", "«реально"):
            self.assertNotIn(meaningful, fillers)


def _has_history():
    return shutil.which("git") and subprocess.run(["git", "cat-file", "-e", "a2feb21^{commit}"], cwd=ROOT,
                                                  capture_output=True).returncode == 0


@unittest.skipUnless(_has_history(), "the original commit is not in the local git history")
class Original(unittest.TestCase):
    def run_original(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, os.path.join(DEMO, "run_original.py")] + list(args), cwd=DEMO,
                           env=env, capture_output=True, text=True, encoding="utf-8")
        return p.stdout.replace("\r\n", "\n")

    def test_before(self):
        self.assertEqual(self.run_original("yt-script/hookscore.py", "--hook", demo.P1), expected("1_hook_original.txt"))
        self.assertEqual(self.run_original("yt-retention/retention.py", "retention_ru.csv"),
                         expected("3_retention_original.txt"))
        self.assertIn("VERDICT       27", expected("1_hook_original.txt"))
        self.assertIn("195.0% lost", expected("3_retention_original.txt"))


if __name__ == "__main__":
    unittest.main()
