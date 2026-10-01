"""English behaviour must not drift. Every case in tests/golden/cases.json is compared byte for byte."""
import os, shutil, subprocess, sys, unittest

from golden import golden


class GoldenEnglish(unittest.TestCase):
    def test_cases(self):
        for case in golden.cases():
            with self.subTest(case=case["id"]):
                want, source = golden.expected(case["id"])
                self.assertIsNotNone(want, f"no expected output for {case['id']} - run golden.py --regenerate")
                self.assertEqual(golden.run(os.path.join(golden.ROOT, "skills"), case), want,
                                 f"{case['id']} differs from tests/golden/{source}/")


def _has_original_ref():
    if not shutil.which("git"):
        return False
    r = subprocess.run(["git", "cat-file", "-e", golden.ORIGINAL_REF + "^{commit}"],
                       cwd=golden.ROOT, capture_output=True)
    return r.returncode == 0


@unittest.skipUnless(_has_original_ref(), "original commit not in local git history")
class GoldenProvenance(unittest.TestCase):
    """tests/golden/orig/ must be exactly what the original commit prints - nobody edited it."""

    def test_orig_matches_original_commit(self):
        hash_dependent = {c["id"] for c in golden.cases() if c.get("hash_dependent")}
        for case_id, text in golden.original_outputs().items():
            if case_id in hash_dependent and sys.version_info < (3, 11):
                continue  # generated on siphash13; 3.9/3.10 use siphash24 and order ties differently
            with self.subTest(case=case_id):
                path = os.path.join(golden.HERE, "orig", case_id + ".txt")
                with open(path, encoding="utf-8", newline="") as fh:
                    self.assertEqual(fh.read(), text)


if __name__ == "__main__":
    unittest.main()
