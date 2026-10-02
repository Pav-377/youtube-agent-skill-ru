#!/usr/bin/env python3
"""check.py - repository checks that are not about what a script outputs.

    python tools/check.py          # run every check, exit 1 if any fails

  sync         every copy in skills/ matches shared/ byte for byte (tools/build.py --check)
  frontmatter  each SKILL.md has a name and description within the Agent Skills limits
  plugin       .claude-plugin/*.json parse and follow the Claude Code naming rules
  links        every relative link in a .md file points at a file that exists
  contained    nothing in a skill folder reaches outside it (no ../)
  text         text files are UTF-8 without a BOM
  imports      skill scripts use the standard library only, and nothing that talks to a network
  skills       a Russian-language mode and examples_ru.md in every skill; tools run from the skill folder

Limits are from the official docs (checked 2026-10-01):
  platform.claude.com/docs/en/agents-and-tools/agent-skills/overview  - SKILL.md frontmatter
  code.claude.com/docs/en/plugins/marketplace-reference              - plugin and marketplace names
"""
import ast, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

IGNORED_DIRS = {".git", "_private", "dist", "__pycache__", ".github"}
TEXT_EXT = {".md", ".py", ".json", ".txt", ".srt", ".vtt", ".csv", ".yml", ".yaml"}
NETWORK = {"socket", "ssl", "urllib", "http", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib",
           "xmlrpc", "requests", "httpx", "aiohttp", "websocket", "websockets"}
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
XML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")


def walk(base, exts=None):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
        for f in sorted(filenames):
            if exts is None or os.path.splitext(f)[1].lower() in exts:
                yield os.path.join(dirpath, f)


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def skill_dirs():
    return [os.path.join(SKILLS, d) for d in sorted(os.listdir(SKILLS))
            if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md"))]


def frontmatter(text):
    """The YAML subset SKILL.md uses: `key: value` and folded/literal blocks (>-, >, |). No PyYAML."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields, key, block, style = {}, None, [], None
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            if key and style:
                fields[key] = (" " if style.startswith(">") else "\n").join(block).strip()
            key, val = m.group(1), m.group(2).strip()
            block, style = [], None
            if val in (">-", ">", "|", "|-"):
                style = val
            else:
                fields[key] = val.strip("\"'")
        elif style is not None:
            block.append(line.strip())
    if key and style:
        fields[key] = (" " if style.startswith(">") else "\n").join(block).strip()
    return fields


# --- checks: each returns a list of problems (strings) --------------------------------------------
def check_sync():
    return [f"skills/{skill}/{name}: {why} - run python tools/build.py" for name, skill, why in build.drift()]


def check_frontmatter():
    out = []
    for d in skill_dirs():
        folder = os.path.basename(d)
        with open(os.path.join(d, "SKILL.md"), encoding="utf-8") as fh:
            fm = frontmatter(fh.read())
        where = f"skills/{folder}/SKILL.md"
        if fm is None:
            out.append(f"{where}: no frontmatter between --- lines")
            continue
        name, desc = fm.get("name", ""), fm.get("description", "")
        if not NAME_RE.match(name):
            out.append(f"{where}: name {name!r} must be 1-64 chars of a-z, 0-9 and -")
        if "anthropic" in name or "claude" in name:
            out.append(f"{where}: name may not contain 'anthropic' or 'claude'")
        if name != folder:
            out.append(f"{where}: name {name!r} differs from the folder name")
        if not desc:
            out.append(f"{where}: description is empty")
        if len(desc) > 1024:
            out.append(f"{where}: description is {len(desc)} chars, the limit is 1024")
        for k, v in (("name", name), ("description", desc)):
            if XML_TAG.search(v):
                out.append(f"{where}: {k} contains an XML tag")
    return out


def check_plugin():
    out, docs = [], {}
    for f in ("plugin.json", "marketplace.json"):
        p = os.path.join(ROOT, ".claude-plugin", f)
        try:
            with open(p, encoding="utf-8") as fh:
                docs[f] = json.load(fh)
        except (OSError, ValueError) as e:
            out.append(f".claude-plugin/{f}: {e}")
    if out:
        return out
    plugin, market = docs["plugin.json"], docs["marketplace.json"]
    for k in ("name", "owner", "plugins"):
        if k not in market:
            out.append(f"marketplace.json: missing required field {k!r}")
    if not (market.get("owner") or {}).get("name"):
        out.append("marketplace.json: owner.name is required")
    if not PLUGIN_ID_RE.match(market.get("name", "")):
        out.append(f"marketplace.json: name {market.get('name')!r} breaks the plugin id rules")
    for i, e in enumerate(market.get("plugins", [])):
        if not PLUGIN_ID_RE.match(e.get("name", "")):
            out.append(f"marketplace.json: plugins[{i}].name {e.get('name')!r} breaks the plugin id rules")
        src = e.get("source")
        if isinstance(src, str) and (".." in src or not (src == "." or src.startswith("./"))):
            out.append(f"marketplace.json: plugins[{i}].source {src!r} must start with ./ and not contain ..")
        if e.get("name") != plugin.get("name"):
            out.append(f"marketplace.json: plugins[{i}].name {e.get('name')!r} differs from plugin.json "
                       f"name {plugin.get('name')!r} - installs by one name fail")
    if not PLUGIN_ID_RE.match(plugin.get("name", "")):
        out.append(f"plugin.json: name {plugin.get('name')!r} breaks the plugin id rules")
    return out


LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def check_links():
    out = []
    for path in walk(ROOT, {".md"}):
        if rel(path).startswith("tests/fixtures/"):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        text = re.sub(r"```.*?```", "", text, flags=re.S)  # code blocks are not links
        for target in LINK.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            file_part = target.split("#", 1)[0]
            if file_part and not os.path.exists(os.path.join(os.path.dirname(path), file_part)):
                out.append(f"{rel(path)}: link to {target} - no such file")
    return out


def check_contained():
    out = []
    for d in skill_dirs():
        for path in walk(d):
            if path.endswith(".md"):
                with open(path, encoding="utf-8") as fh:
                    if "../" in fh.read():
                        out.append(f"{rel(path)}: refers to ../ - a skill must not reach outside its folder")
            elif path.endswith(".py"):
                with open(path, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) and \
                            (node.value == ".." or "../" in node.value or "..\\" in node.value):
                        out.append(f"{rel(path)}:{node.lineno}: path leaves the skill folder ({node.value!r})")
    return out


def check_text():
    out = []
    for path in walk(ROOT, TEXT_EXT):
        with open(path, "rb") as fh:
            data = fh.read()
        if data.startswith(b"\xef\xbb\xbf"):
            out.append(f"{rel(path)}: starts with a UTF-8 BOM")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as e:
            out.append(f"{rel(path)}: not UTF-8 ({e})")
    return out


def check_imports():
    out = []
    stdlib = getattr(sys, "stdlib_module_names", None)  # Python 3.10+
    for base in (SKILLS, os.path.join(ROOT, "shared")):
        for path in walk(base, {".py"}):
            local = {os.path.splitext(f)[0] for f in os.listdir(os.path.dirname(path)) if f.endswith(".py")}
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names = [node.module]
                for n in names:
                    top = n.split(".")[0]
                    if top in NETWORK:
                        out.append(f"{rel(path)}:{node.lineno}: imports {n} - skills never touch the network")
                    elif stdlib is not None and top not in stdlib and top not in local:
                        out.append(f"{rel(path)}:{node.lineno}: imports {n}, which is not the standard library")
    return out


def check_skills():
    """Every skill has a Russian-language mode and its examples, and runs its tools from its own folder."""
    out = []
    for d in skill_dirs():
        name = os.path.basename(d)
        with open(os.path.join(d, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        if "## Russian-language mode" not in text:
            out.append(f"skills/{name}/SKILL.md: no '## Russian-language mode' section")
        if not os.path.isfile(os.path.join(d, "examples_ru.md")):
            out.append(f"skills/{name}: no examples_ru.md")
        elif "(examples_ru.md)" not in text:
            out.append(f"skills/{name}/SKILL.md: does not link examples_ru.md")
        for m in re.finditer(r"python3?\s+([\w./${}\"]+\.py)", text):
            if "CLAUDE_SKILL_DIR" not in m.group(1):
                out.append(f"skills/{name}/SKILL.md: '{m.group(0)}' - run tools as python3 \"${{CLAUDE_SKILL_DIR}}/x.py\"")
    short = build.claude_ai_descriptions()
    for d in skill_dirs():
        name = os.path.basename(d)
        desc = short["descriptions"].get(name)
        if desc is None:
            out.append(f"tools/claude_ai_descriptions.json: no short description for {name}")
        elif len(desc) > short["max_chars"]:
            out.append(f"tools/claude_ai_descriptions.json: {name} is {len(desc)} chars, claude.ai takes {short['max_chars']}")
    for src, copy in (("templates/voice.md", "shared/voice_template.md"),
                      ("templates/voice.ru.md", "shared/voice_template.ru.md")):
        a, b = os.path.join(ROOT, src), os.path.join(ROOT, copy)
        if os.path.exists(a) and os.path.exists(b):
            with open(a, "rb") as fa, open(b, "rb") as fb:
                if fa.read() != fb.read():
                    out.append(f"{copy} differs from {src} - copy the template over")
    return out


CHECKS = [("sync", check_sync), ("frontmatter", check_frontmatter), ("plugin", check_plugin),
          ("links", check_links), ("contained", check_contained), ("text", check_text),
          ("imports", check_imports), ("skills", check_skills)]


def main():
    failed = 0
    for name, fn in CHECKS:
        problems = fn()
        print(f"  {'ok  ' if not problems else 'FAIL'}  {name}")
        for p in problems:
            print(f"          {p}")
        failed += bool(problems)
    print(f"\n  {len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
