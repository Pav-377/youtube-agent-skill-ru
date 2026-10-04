#!/usr/bin/env python3
"""rebrand.py - put the publisher's names into the repository and rebuild dist/.

    python tools/rebrand.py              # apply branding.json, then build dist/
    python tools/rebrand.py --no-dist    # apply branding.json only
    python tools/rebrand.py --check      # change nothing; list files that still hold placeholders

branding.json holds the GitHub owner, the repository name, the author for LICENSE and the plugin
manifests, the repository link, and the plugin and marketplace names. The files hold placeholders:
{{OWNER}}, {{REPO}}, {{REPO_URL}}, {{AUTHOR}}. Every placeholder is replaced; the plugin and
marketplace names are replaced wherever they appear as whole names.

Running it again with other values works too: the values applied last time are kept in
branding.json under "applied" and are replaced like placeholders. tests/ is never changed.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDING = os.path.join(ROOT, "branding.json")
TOKENS = ("OWNER", "REPO", "REPO_URL", "AUTHOR")
TOKEN_RE = re.compile(r"\{\{(?:%s)\}\}" % "|".join(TOKENS))
SKIP_DIRS = {".git", "_private", "dist", "__pycache__", "tests"}
SKIP_FILES = {"branding.json", os.path.join("tools", "rebrand.py")}
TEXT_EXT = {".md", ".py", ".json", ".txt", ".yml", ".yaml", ".csv"}
TEXT_NAMES = {"LICENSE"}
AUTHOR_FILES = {"LICENSE", os.path.join(".claude-plugin", "plugin.json"), os.path.join(".claude-plugin", "marketplace.json")}
EDGE = "A-Za-z0-9_-"
RULES = {
    "owner": (r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$", "a GitHub user or organisation name: letters, digits, '-'"),
    "repo": (r"^[A-Za-z0-9._-]{1,100}$", "a repository name: letters, digits, '.', '_', '-'"),
    "plugin": (r"^[a-z0-9]+(?:-[a-z0-9]+)*$", "lower-case letters, digits and '-'"),
    "marketplace": (r"^[a-z0-9]+(?:-[a-z0-9]+)*$", "lower-case letters, digits and '-'"),
}


def text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
            if rel in SKIP_FILES:
                continue
            if os.path.splitext(f)[1].lower() in TEXT_EXT or f in TEXT_NAMES:
                yield rel


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", newline="") as fh:
        return fh.read()


def load():
    with open(BRANDING, encoding="utf-8") as fh:
        b = json.load(fh)
    problems = []
    for key in ("owner", "repo", "author", "plugin", "marketplace"):
        v = (b.get(key) or "").strip()
        b[key] = v
        if not v or "{{" in v:
            problems.append(f"branding.json: fill in {key!r}")
        elif key in RULES and not re.match(RULES[key][0], v):
            problems.append(f"branding.json: {key} {v!r} must be {RULES[key][1]}")
    if "\n" in b["author"]:
        problems.append("branding.json: author must be one line")
    b["repo_url"] = (b.get("repo_url") or "").strip().rstrip("/") or f"https://github.com/{b['owner']}/{b['repo']}"
    if not b["repo_url"].startswith("https://"):
        problems.append("branding.json: repo_url must start with https://")
    return b, problems


def current_names():
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        plugin = json.load(fh)["name"]
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
        market = json.load(fh)["name"]
    return plugin, market


def mapping(b):
    """old text -> new text. One pass, longest first, whole names only."""
    new = {"{{OWNER}}": b["owner"], "{{REPO}}": b["repo"], "{{REPO_URL}}": b["repo_url"]}
    old_plugin, old_market = current_names()
    new[old_plugin] = b["plugin"]
    new[old_market] = b["marketplace"]
    a = b.get("applied") or {}
    if a:
        new[a["repo_url"]] = b["repo_url"]
        new[f"{a['owner']}/{a['repo']}"] = f"{b['owner']}/{b['repo']}"
        new[f"https://github.com/{a['owner']}"] = f"https://github.com/{b['owner']}"
    return {k: v for k, v in new.items() if k != v}


def author_mapping(b):
    old = [("{{AUTHOR}}", b["author"])]
    a = b.get("applied") or {}
    if a.get("author") and a["author"] != b["author"]:
        old.append((a["author"], b["author"]))
    return old


def substitute(text, table, as_json):
    if not table:
        return text
    keys = sorted(table, key=len, reverse=True)
    rx = re.compile(f"(?<![{EDGE}])(?:" + "|".join(map(re.escape, keys)) + f")(?![{EDGE}])")
    esc = (lambda v: json.dumps(v, ensure_ascii=False)[1:-1]) if as_json else (lambda v: v)
    return rx.sub(lambda m: esc(table[m.group(0)]), text)


def leftovers():
    return [rel for rel in text_files() if TOKEN_RE.search(read(rel))]


def main():
    if "--check" in sys.argv[1:]:
        left = leftovers()
        for rel in left:
            print(f"  placeholders left in {rel}")
        sys.exit(1 if left else 0)
    b, problems = load()
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    table = mapping(b)
    changed = []
    for rel in text_files():
        text = read(rel)
        as_json = rel.endswith(".json")
        out = substitute(text, table, as_json)
        for old, new in author_mapping(b):
            if old == "{{AUTHOR}}" or rel in AUTHOR_FILES:  # an old name is replaced only where it was put
                out = out.replace(old, json.dumps(new, ensure_ascii=False)[1:-1] if as_json else new)
        if out != text:
            with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
            changed.append(rel)
    for rel in changed:
        print(f"  {rel}")
    print(f"  {len(changed)} files changed")
    raw = json.load(open(BRANDING, encoding="utf-8"))
    raw["applied"] = {k: b[k] for k in ("owner", "repo", "author", "repo_url", "plugin", "marketplace")}
    with open(BRANDING, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    left = leftovers()
    if left:
        print("  placeholders left in: " + ", ".join(left))
        sys.exit(1)
    if "--no-dist" not in sys.argv[1:]:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py"), "--dist"], cwd=ROOT)
        if r.returncode:
            sys.exit(r.returncode)
        print("  dist/ rebuilt")


if __name__ == "__main__":
    main()
