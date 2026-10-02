#!/usr/bin/env python3
"""run_original.py - run a script of the ORIGINAL plugin (commit a2feb21) for the before/after demo.

    cd demo
    python run_original.py yt-script/hookscore.py --hook "..."
    python run_original.py yt-retention/retention.py retention_ru.csv

The original is unpacked from this repository's git history into a temporary folder, so nothing
needs to be cloned. Needs git and the full history (a normal clone has it).
"""
import io, os, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = "a2feb21"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    data = subprocess.run(["git", "archive", "--format=zip", REF, "skills"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        # file arguments stay as given: the script runs in the caller's folder, and the original
        # prints the path it was given at the top of its report
        p = subprocess.run([sys.executable, os.path.join(tmp, "skills", sys.argv[1])] + sys.argv[2:], env=env)
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
