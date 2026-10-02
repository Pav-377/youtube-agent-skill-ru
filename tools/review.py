#!/usr/bin/env python3
"""review.py - hand a labelled test set to the channel owner as one Excel-friendly table, and take
their corrections back.

    python tools/review.py export hooks _private/review/hooks_ru.csv
    python tools/review.py import hooks _private/review/hooks_ru.csv     # prints what changed, saves

The table opens in Excel on a Russian Windows by double click: ';' between columns, UTF-8 with a
BOM. Columns: №, текст, твоя разметка (Claude's label), почему, моя оценка (empty). The owner
writes in «моя оценка» only where they disagree: «сильный» / «слабый» for a hook, anything for a
translation pair. Disputed cases come first.

On import every non-empty «моя оценка» is applied (hook labels) or listed (comments), and the set's
status records that the owner reviewed it. Excel may save the file back as cp1251 or with another
separator; both are read.
"""
import csv, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))
import lang  # noqa: E402

SETS = {"hooks": os.path.join(ROOT, "tests", "fixtures", "hooks_ru.json")}
COLUMNS = ["№", "текст", "твоя разметка", "почему", "моя оценка"]
LABEL_RU = {"strong": "сильный", "weak": "слабый"}


def rows_for_hooks(doc):
    hooks = sorted(doc["hooks"], key=lambda h: not h["disputed"])  # disputed first, order kept
    for h in hooks:
        why = ("СПОРНО: " if h["disputed"] else "") + h["why"]
        yield [h["id"], h["text"], LABEL_RU[h["label"]], why, ""]
    for p in doc["pairs"]:
        yield [p["id"], f"RU: {p['ru']}\nEN: {p['en']}", "перевод равнозначный",
               "русская и английская версии должны получить близкие оценки", ""]


def export(name, path):
    with open(SETS[name], encoding="utf-8") as fh:
        doc = json.load(fh)
    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    w.writerow(COLUMNS)
    rows = list(rows_for_hooks(doc))
    w.writerows(rows)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(out.getvalue())
    print(f"  {len(rows)} rows -> {path}")


def parse_label(value):
    v = lang.normalize(value).strip()
    if v.startswith("сил") or v in ("+", "strong"):
        return "strong"
    if v.startswith("сла") or v in ("-", "weak"):
        return "weak"
    return None


def import_(name, path):
    with open(SETS[name], encoding="utf-8") as fh:
        doc = json.load(fh)
    text = lang.read_text(path)
    first = text.splitlines()[0] if text else ""
    delim = max(";,\t", key=first.count)
    table = list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))
    head, body = table[0], table[1:]
    i_id, i_note = head.index("№"), head.index("моя оценка")
    hooks = {h["id"]: h for h in doc["hooks"]}
    changed, comments = [], []
    for r in body:
        if len(r) <= i_note or not r[i_note].strip():
            continue
        rid, note = r[i_id], r[i_note].strip()
        label = parse_label(note) if rid in hooks else None
        if label and label != hooks[rid]["label"]:
            changed.append((rid, hooks[rid]["label"], label))
            hooks[rid]["label"] = label
            hooks[rid]["owner_changed"] = True
        elif not label:
            comments.append((rid, note))
            (hooks.get(rid) or next(p for p in doc["pairs"] if p["id"] == rid))["owner_note"] = note
    doc["status"] = f"reviewed by the owner: {len(changed)} label(s) changed, {len(comments)} comment(s)"
    with open(SETS[name], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for rid, a, b in changed:
        print(f"  {rid}: {a} -> {b}")
    for rid, note in comments:
        print(f"  {rid}: comment: {note}")
    print(f"  {doc['status']}")


def main():
    lang.setup_output()
    a = sys.argv[1:]
    if len(a) != 3 or a[0] not in ("export", "import") or a[1] not in SETS:
        print(__doc__)
        sys.exit(1)
    (export if a[0] == "export" else import_)(a[1], a[2])


if __name__ == "__main__":
    main()
