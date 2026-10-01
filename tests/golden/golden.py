"""golden.py - run the English regression cases and regenerate the original's expected output.

    python tests/golden/golden.py --regenerate     # rewrite tests/golden/orig/ from commit a2feb21

The expected output in tests/golden/orig/ is never edited by hand. It is what the original scripts
at ORIGINAL_REF print for each case in cases.json. When our version changes English behaviour on
purpose, the new expectation goes into tests/golden/current/<id>.txt and the change is listed in
CHANGELOG.md. test_golden.py prefers current/ over orig/.
"""
import io, json, os, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "tests", "golden")
FIXTURES_EN = os.path.join(ROOT, "tests", "fixtures", "en")
ORIGINAL_REF = "a2feb21"


def cases():
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def run(skills_root, case):
    """Run one case against a skills/ tree. Returns the text that is compared: exit code + stdout."""
    # PYTHONHASHSEED: the original chapters.py orders tied keywords by set iteration order, which
    # changes from run to run. A fixed seed makes the original reproducible (on one hash algorithm:
    # Python 3.11 moved from siphash24 to siphash13, hence "hash_dependent" in cases.json).
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    p = subprocess.run([sys.executable, os.path.join(skills_root, case["script"])] + case["args"],
                       cwd=FIXTURES_EN, env=env, capture_output=True, text=True, encoding="utf-8")
    return f"exit={p.returncode}\n{p.stdout}"


def expected(case_id):
    for sub in ("current", "orig"):
        path = os.path.join(HERE, sub, case_id + ".txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                return fh.read(), sub
    return None, None


def extract_original(dest, ref=ORIGINAL_REF):
    """Unpack skills/ as it was at `ref` into dest. Needs the git history (fetch-depth 0 in CI)."""
    data = subprocess.run(["git", "archive", "--format=zip", ref, "skills"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    return os.path.join(dest, "skills")


def original_outputs():
    with tempfile.TemporaryDirectory() as tmp:
        skills = extract_original(tmp)
        return {c["id"]: run(skills, c) for c in cases()}


def regenerate():
    out = os.path.join(HERE, "orig")
    os.makedirs(out, exist_ok=True)
    for case_id, text in original_outputs().items():
        with open(os.path.join(out, case_id + ".txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"  {case_id}")


if __name__ == "__main__":
    if "--regenerate" in sys.argv:
        regenerate()
    else:
        print(__doc__)
