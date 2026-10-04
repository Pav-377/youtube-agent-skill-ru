#!/usr/bin/env python3
# Source of truth: shared/aitells.py (and shared/aitells.json). tools/build.py copies them into
# yt-script, yt-shorts and yt-package. Edit these files, never a copy.
"""aitells.py - find the phrases that make a script sound machine-written, before anyone reads it aloud.

    python3 aitells.py script.txt              # paragraphs separated by an empty line
    python3 aitells.py --text "Это не просто монтаж, а целая философия."
    python3 aitells.py script.txt --json
    python3 aitells.py script.txt --lang ru    # ru, en or auto (the default)
    python3 aitells.py script.txt --long 22    # a different limit for a long sentence

Two kinds of finding:
  stamp    a pattern machine-written text leans on: "not X, but Y" contrasts, canned linking
           phrases, lead-in questions, slogan-like parallels, triads one after another
  speech   advice for text that will be spoken: a sentence too long for one breath, too many dashes

It changes nothing. Each finding names the paragraph and sentence, quotes the words, and says how to
say it more simply; Claude rewrites those places (see the skill's SKILL.md). All patterns are in
aitells.json.
"""
import json, os, re, sys

import lang

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = lang.read_json(os.path.join(HERE, "aitells.json"))
DASH = re.compile(r"\s[—–-]\s")


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def sentences(par):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", par.replace("\n", " ")) if s.strip()]


def phrase_rx(p):
    body = re.escape(lang.normalize(p)).replace(r"\*", r"\w*").replace(r"\ ", r"[\s,]+")
    return re.compile(r"(?<!\w)" + body + r"(?!\w)")


def parallel_halves(s, rule):
    """Two short halves around one dash that share a word: Твой контент — твои правила."""
    if "halves" not in rule:
        return False
    parts = DASH.split(" " + s.strip().rstrip(".!") + " ")
    if len(parts) != 2:
        return False
    a, b = (lang.words(p) for p in parts)
    n = rule["halves"]["max_words"]
    return 0 < len(a) <= n and 0 < len(b) <= n and any(lang.same_word(x, y) for x in a for y in b)


def check(text, code):
    rules = DATA[code]
    out = []

    def add(pi, si, rule, quote, extra=""):
        r = rules[rule]
        out.append({"paragraph": pi + 1, "sentence": si + 1 if si is not None else None, "kind": r["kind"],
                    "type": rule, "label": r["label"] + extra, "quote": quote.strip(), "hint": r["hint"]})

    compiled = {name: [re.compile(x, re.I) for x in r.get("regex", [])] for name, r in rules.items()}
    phrases = {name: [phrase_rx(p) for p in r.get("phrases", [])] for name, r in rules.items()}
    for pi, par in enumerate(paragraphs(text)):
        sents = sentences(par)
        triads = []
        for si, s in enumerate(sents):
            norm = lang.normalize(s)
            for name in ("contrast", "canned", "lead_in"):
                hit = next((m.group(0) for rx in compiled[name] for m in [rx.search(s)] if m), None)
                if hit is None:
                    hit = next((m.group(0) for rx in phrases[name] for m in [rx.search(norm)] if m), None)
                if hit:
                    add(pi, si, name, hit)
            nxt = rules["contrast"].get("next_sentence")
            if nxt and si + 1 < len(sents) and re.search(nxt["first"], norm) and \
                    re.search(nxt["second"], lang.normalize(sents[si + 1])) and \
                    not any(f["paragraph"] == pi + 1 and f["sentence"] == si + 1 and f["type"] == "contrast" for f in out):
                add(pi, si, "contrast", s + " " + sents[si + 1])
            words = len(lang.tokens(s))
            if si == len(sents) - 1 and words <= rules["aphorism"]["max_words"] and \
                    (any(rx.search(s) for rx in compiled["aphorism"]) or parallel_halves(s, rules["aphorism"])):
                add(pi, si, "aphorism", s)
            if any(rx.search(s) for rx in compiled["triad"]):
                triads.append(si)
            if words > rules["long"]["max_words"]:
                add(pi, si, "long", s[:80] + ("…" if len(s) > 80 else ""), f" ({words} " +
                    (lang.plural(words, "слово", "слова", "слов") if code == "ru" else "words") + ")")
        if len(triads) >= rules["triad"]["min_in_paragraph"]:
            add(pi, triads[1], "triad", sents[triads[1]][:80])
        dashes = len(DASH.findall(" " + par + " "))
        if dashes > rules["dashes"]["max_per_paragraph"]:
            add(pi, None, "dashes", par[:60] + "…", f" ({dashes})")
    return out


def report(found, code):
    if not found:
        print("\n  Штампов не найдено.\n" if code == "ru" else "\n  No AI tells found.\n")
        return
    stamps = sum(f["kind"] == "stamp" for f in found)
    print()
    for f in found:
        where = (f"абзац {f['paragraph']}" if code == "ru" else f"paragraph {f['paragraph']}") + \
                (f", {'предложение' if code == 'ru' else 'sentence'} {f['sentence']}" if f["sentence"] else "")
        mark = "штамп" if code == "ru" and f["kind"] == "stamp" else "устная речь" if code == "ru" else f["kind"]
        print(f"  {where}  [{mark}] {f['label']}")
        print(f"      «{f['quote']}»" if code == "ru" else f"      \"{f['quote']}\"")
        print(f"      {f['hint']}")
    if code == "ru":
        print(f"\n  Штампов: {stamps}, советов для устной речи: {len(found) - stamps}. "
              "Скрипт ничего не переписывает: перепишите эти места своими словами.\n")
    else:
        print(f"\n  {stamps} AI tells, {len(found) - stamps} speech notes. Nothing was rewritten.\n")


USAGE_RU = """aitells.py — поиск штампов машинного текста в сценарии.

    python3 aitells.py сценарий.txt              # абзацы разделены пустой строкой
    python3 aitells.py --text "Это не просто монтаж, а целая философия."
    python3 aitells.py сценарий.txt --json       # вывод в JSON
    python3 aitells.py сценарий.txt --lang ru    # язык: ru, en или auto (по умолчанию)
    python3 aitells.py сценарий.txt --long 22    # другой порог длинного предложения

Скрипт ничего не переписывает. Для каждой находки он показывает цитату и подсказку.
"""


def main():
    lang.setup_output()
    a = sys.argv[1:]
    choice, a = lang.take_lang_flag(a)
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    if "--long" in a:
        limit = lang.flag_value(a, "--long", cast=int)
        for code in lang.LANGS:
            DATA[code]["long"]["max_words"] = limit
        i = a.index("--long")
        a = a[:i] + a[i + 2:]
    if "--text" in a:
        text = lang.flag_value(a, "--text")
    elif a and os.path.exists(a[0]):
        text = lang.read_text(a[0])
    else:
        lang.usage(__doc__, USAGE_RU, choice, missing=a[0] if a else None)
    code = lang.resolve(choice, text)
    found = check(text, code)
    if as_json:
        print(json.dumps({"lang": code, "findings": found}, indent=1, ensure_ascii=False)); return
    report(found, code)


if __name__ == "__main__":
    main()
