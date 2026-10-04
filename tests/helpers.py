"""Shared helpers for the test suite. Standard library only."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
# Help and error messages follow the system locale. Tests pin it, so a run does not depend on the
# machine: English unless a test passes LOCALE_RU.
LOCALE_EN = {"LC_ALL": "", "LC_MESSAGES": "", "LANGUAGE": "", "LANG": "en_US.UTF-8"}
LOCALE_RU = {"LC_ALL": "", "LC_MESSAGES": "", "LANGUAGE": "", "LANG": "ru_RU.UTF-8"}


def run_script(script, *args, cwd=None, env=None, skills_root=SKILLS):
    """Run skills/<script> with args. Returns CompletedProcess with text stdout/stderr (UTF-8)."""
    e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", **LOCALE_EN)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, os.path.join(skills_root, script)] + [str(a) for a in args],
                          cwd=cwd or FIXTURES, env=e, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run_json(script, *args, **kw):
    p = run_script(script, *args, "--json", **kw)
    if p.returncode != 0:
        raise AssertionError(f"{script} exited {p.returncode}: {p.stdout}{p.stderr}")
    return json.loads(p.stdout)


def fixture(*parts):
    return os.path.join(FIXTURES, *parts)
