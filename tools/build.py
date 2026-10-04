#!/usr/bin/env python3
"""build.py - copy shared/ into the skill folders, and pack the release zips.

    python tools/build.py              # sync shared/ -> skills/ (what shared/manifest.json says)
    python tools/build.py --check      # change nothing; exit 1 and list every copy that drifted
    python tools/build.py --dist       # sync, then write dist/: one zip per skill + the whole plugin
    python tools/build.py --dist --out some/dir

Why copies at all: claude.ai takes one skill per zip, so a skill that reads ../yt-script/hooks.json
works in Claude Code and breaks the moment it is uploaded on its own. Every skill carries what it
needs; shared/ is the one place those files are edited.

The zips are deterministic: sorted entries, fixed timestamps, no __pycache__. Building twice gives
byte-identical files, so a release can be checked against a rebuild.
"""
import json, os, re, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(ROOT, "shared")
SKILLS = os.path.join(ROOT, "skills")
with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as _fh:
    PLUGIN_NAME = json.load(_fh)["name"]  # the whole-plugin zip is named after the marketplace
# What goes into the whole-plugin zip, in addition to skills/. Missing entries are skipped.
PLUGIN_EXTRA = [".claude-plugin", "templates", "docs", "README.md", "README.en.md", "LICENSE", "CHANGELOG.md"]
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
SKIP = {"__pycache__", ".DS_Store"}


def manifest():
    with open(os.path.join(SHARED, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)["files"]


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def drift():
    """[(shared file, skill, problem)] for every copy that is missing or differs."""
    out = []
    for name, skills in manifest().items():
        src = read(os.path.join(SHARED, name))
        for skill in skills:
            dst = os.path.join(SKILLS, skill, name)
            if not os.path.exists(dst):
                out.append((name, skill, "missing"))
            elif read(dst) != src:
                out.append((name, skill, "differs from shared/"))
    return out


def sync():
    changed = []
    for name, skills in manifest().items():
        src = os.path.join(SHARED, name)
        for skill in skills:
            if not os.path.isdir(os.path.join(SKILLS, skill)):
                raise SystemExit(f"manifest names skills/{skill}, which does not exist")
            dst = os.path.join(SKILLS, skill, name)
            if not os.path.exists(dst) or read(dst) != read(src):
                shutil.copyfile(src, dst)
                changed.append(f"{skill}/{name}")
    return changed


def _files(base):
    """Every file under base, sorted, relative paths with forward slashes."""
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        for f in sorted(filenames):
            if f not in SKIP and not f.endswith(".pyc"):
                out.append(os.path.relpath(os.path.join(dirpath, f), base).replace(os.sep, "/"))
    return out


def _write_zip(path, entries):
    """entries: [(name inside the zip, file on disk - or the bytes themselves)]."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in sorted(entries, key=lambda e: e[0]):
            info = zipfile.ZipInfo(arc, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src if isinstance(src, bytes) else read(src))


def claude_ai_descriptions():
    with open(os.path.join(ROOT, "tools", "claude_ai_descriptions.json"), encoding="utf-8") as fh:
        return json.load(fh)


def claude_ai_skill_md(skill):
    """SKILL.md for a claude.ai upload: the same file with the short description claude.ai accepts
    (200 characters there, 1024 in Claude Code and plugins)."""
    short = claude_ai_descriptions()["descriptions"][skill]
    with open(os.path.join(SKILLS, skill, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    quoted = '"' + short.replace("\\", "\\\\").replace('"', '\\"') + '"'
    new, n = re.subn(r"\A(---\nname: [^\n]+\n)description: >-\n(?:  [^\n]*\n)+(---\n)",
                     lambda m: f"{m.group(1)}description: {quoted}\n{m.group(2)}", text)
    if n != 1:
        raise SystemExit(f"skills/{skill}/SKILL.md: frontmatter not in the expected shape")
    return new.encode("utf-8")


def dist(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for skill in sorted(os.listdir(SKILLS)):
        base = os.path.join(SKILLS, skill)
        if not os.path.isfile(os.path.join(base, "SKILL.md")):
            continue
        # The skill folder is the top level of its zip: yt-script.zip -> yt-script/SKILL.md
        entries = [(f"{skill}/{rel}", claude_ai_skill_md(skill) if rel == "SKILL.md" else os.path.join(base, rel))
                   for rel in _files(base)]
        path = os.path.join(out_dir, f"{skill}.zip")
        _write_zip(path, entries)
        written.append(path)
    entries = []
    for top in ["skills"] + PLUGIN_EXTRA:
        p = os.path.join(ROOT, top)
        if os.path.isdir(p):
            entries += [(f"{PLUGIN_NAME}/{top}/{rel}", os.path.join(p, rel)) for rel in _files(p)]
        elif os.path.isfile(p):
            entries.append((f"{PLUGIN_NAME}/{top}", p))
    path = os.path.join(out_dir, f"{PLUGIN_NAME}.zip")
    _write_zip(path, entries)
    written.append(path)
    return written


def main():
    a = sys.argv[1:]
    if "--check" in a:
        bad = drift()
        for name, skill, why in bad:
            print(f"  skills/{skill}/{name}: {why} - run python tools/build.py")
        sys.exit(1 if bad else 0)
    for c in sync():
        print(f"  synced skills/{c}")
    if "--dist" in a:
        out = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "dist")
        for p in dist(out):
            print(f"  wrote {p}")


if __name__ == "__main__":
    main()
