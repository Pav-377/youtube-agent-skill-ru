#!/usr/bin/env python3
# Source of truth: shared/hookscore.py. tools/build.py copies it into yt-script, yt-shorts and yt-audit.
# Edit this file, never a copy.
"""hookscore.py - score a YouTube hook before you waste a take on it.

What it is for: it filters out weak openings and says what to fix. It does not predict views.

Five properties, 0-100 each, and a verdict that is 60% the mean and 40% the weakest one. The
weakest-link weighting is deliberate: a hook with four strong properties and one dead one is a hook
that leaks at the dead one, and averaging hides that.

    python3 hookscore.py hooks.txt            # one hook per line, ranked
    python3 hookscore.py --hook "one line"    # score a single hook
    python3 hookscore.py --json hooks.txt     # machine-readable

WHAT THIS CAN AND CANNOT TELL YOU. Measured against 74 real short-form hooks (first 15 seconds of
auto-captions, top-8 and bottom-8 by views across five channels): it separates deliberately bad
hooks from real ones well, and it separates a creator's own hits from their own misses barely at
all. Treat a low score as a reason to look again, never a high score as a promise.

The Russian mode was measured the same way (tools/research/eval_hooks.py): on hooks written to be
weak or ordinary it ranks the ordinary one higher in 98% of pairs, with a 15-point gap; on the first
15 seconds of 226 real Russian videos, strong (2x the channel median views) and weak (under 0.5x)
score the same on average. A filter for weak openings, not a forecast.
"""
import json, os, re, sys

import lang

HERE = os.path.dirname(os.path.abspath(__file__))
FORMULAS = lang.read_json(os.path.join(HERE, "hooks.json"))["hooks"]

FILLER = {"basically","actually","literally","just","really","very","so","kind","sort","like",
          "guys","hey","welcome","today","video","subscribe","channel"}
VAGUE = {"amazing","incredible","insane","crazy","huge","massive","game","changer","secret",
         "powerful","ultimate","best","revolutionary","mind","blowing","unbelievable"}
CONCRETE = re.compile(r"\b(\d[\d,.]*\s?(%|k|m|x|s|m|h)?|\$\d|\d+\s?(second|minute|hour|day|week|month|year)s?)\b", re.I)
YOU = re.compile(r"\b(you|your|you're|youre|yourself)\b", re.I)
STAKE = re.compile(r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|before|stop|never|die|dying|dead)\b", re.I)
CURIOSITY = re.compile(r"\b(why|how|what|which|until|before|but|nobody|almost|except|reason|actually)\b", re.I)

def words(t):
    # Dots at the edge are punctuation, not part of the word: "video." has to match "video" in the
    # word lists, and a lone "..." is not a word. Inner dots stay, so "3.5" is still one token.
    return [w for w in (x.strip(".") for x in re.findall(r"[a-z0-9'%$.]+", t.lower())) if w]

def specificity(t):
    w = words(t)
    if not w: return 0
    nums = len(CONCRETE.findall(t))
    vague = sum(1 for x in w if x in VAGUE)
    filler = sum(1 for x in w if x in FILLER)
    s = 34 + nums * 22 - vague * 16 - filler * 5
    # proper nouns that are not sentence-initial read as named things
    # Known quirk, kept on purpose in English: only the hook's very first word is skipped, so the
    # first word of a second sentence counts as a name too. Fixing it made strong and weak hooks
    # harder to tell apart (strong hooks are often two short sentences). See CHANGELOG.md.
    s += min(18, 6 * sum(1 for x in t.split()[1:] if x[:1].isupper()))
    return max(0, min(100, s))

def address(t):
    n = len(YOU.findall(t))
    first = 30 if YOU.search(" ".join(t.split()[:6])) else 0
    return max(0, min(100, 26 + n * 20 + first))

def stakes(t):
    n = len(STAKE.findall(t))
    return max(0, min(100, 22 + n * 26 + (14 if CONCRETE.search(t) else 0)))

def curiosity(t):
    n = len(CURIOSITY.findall(t))
    q = 18 if t.strip().endswith("?") else 0
    # a hook that resolves itself has no gap left
    closed = -18 if re.search(r"\b(because|so that|which means)\b", t, re.I) else 0
    return max(0, min(100, 24 + n * 17 + q + closed))

def brevity(t):
    n = len(words(t))
    if n == 0: return 0
    # 9-24 words is the band a spoken hook lands in at ~150wpm inside 10 seconds
    if 9 <= n <= 24: return 100
    if n < 9:  return max(30, 100 - (9 - n) * 11)
    return max(10, 100 - (n - 24) * 7)

PROPS = [("SPECIFICITY", specificity), ("ADDRESS", address), ("STAKES", stakes),
         ("CURIOSITY", curiosity), ("BREVITY", brevity)]

# --- Russian ---------------------------------------------------------------------------------------
# The same five properties and the same arithmetic as above, with Russian word lists from
# hookscore.json. Words are lang.tokens(), so Cyrillic, hyphens and numbers count, and punctuation
# never does. Unlike the English mode, the first word of every sentence is never taken for a name.
RU = lang.read_json(os.path.join(HERE, "hookscore.json"))
ADDR = RU["address_ru"]
PRONOUNS = {lang.normalize(w) for w in ADDR["pronouns"]}
IMPERATIVES = [lang.normalize(w) for w in ADDR["imperatives"]]
SENTENCE_END = (".", "!", "?", "…")

def ru_tokens(t): return [lang.normalize(w) for w in lang.tokens(t)]

def ru_hits(t, entries):
    """How many times the entries occur: stem* by prefix, phrases as whole words, others by form."""
    toks = ru_tokens(t)
    text = " " + " ".join(toks) + " "
    n = 0
    for e in entries:
        e = lang.normalize(e)
        if " " in e:
            n += len(re.findall(r"(?<!\w)" + re.escape(e) + r"(?!\w)", text))
        elif e.endswith("*"):
            n += sum(1 for w in toks if w.startswith(e[:-1]))
        elif len(e) < 5:
            n += sum(1 for w in toks if w == e)  # short words by form would merge как and какой
        else:
            n += sum(1 for w in toks if len(w) >= 5 and lang.same_word(w, e))
    return n

def ru_numbers(t):
    """Runs of digits and number words: "пять тысяч" is one figure, "30 дней" another."""
    groups, inside = 0, False
    for w in ru_tokens(t):
        is_num = w[0].isdigit() or any(lang.same_word(w, x) for x in RU["numerals_ru"])
        groups += is_num and not inside
        inside = is_num
    return groups

def ru_names(t):
    toks = t.split()
    n = 0
    for i, tok in enumerate(toks):
        w = re.sub(r"^\W+|\W+$", "", tok)
        if i == 0 or toks[i - 1].endswith(SENTENCE_END):
            continue  # a sentence start is not a name
        if w[:1].isupper() and not (len(w) > 1 and w.isupper()):
            n += 1
    return n

def ru_address_positions(t):
    toks = ru_tokens(t)
    text = " " + " ".join(toks) + " "
    pos = [i for i, w in enumerate(toks) if w in PRONOUNS or w in IMPERATIVES
           or (len(w) >= ADDR["second_person_min_length"] and w.endswith(tuple(ADDR["second_person_endings"])))]
    for e in IMPERATIVES:
        if " " in e:
            for m in re.finditer(r"(?<!\w)" + re.escape(e) + r"(?!\w)", text):
                pos.append(text[:m.start()].count(" ") - 1)  # the text starts with a space
    return pos

def specificity_ru(t):
    if not ru_tokens(t): return 0
    s = 34 + ru_numbers(t) * 22 - ru_hits(t, RU["vague_ru"]) * 16 - ru_hits(t, RU["filler_ru"]) * 5
    s += min(18, 6 * ru_names(t))
    return max(0, min(100, s))

def address_ru(t):
    pos = ru_address_positions(t)
    first = 30 if any(p < 6 for p in pos) else 0
    return max(0, min(100, 26 + len(pos) * 20 + first))

def stakes_ru(t):
    n = ru_hits(t, RU["stakes_ru"])
    return max(0, min(100, 22 + n * 26 + (14 if ru_numbers(t) else 0)))

def curiosity_ru(t):
    n = ru_hits(t, RU["curiosity_ru"])
    q = 18 if t.strip().endswith("?") else 0
    closed = -18 if ru_hits(t, RU["closed_ru"]) else 0
    return max(0, min(100, 24 + n * 17 + q + closed))

def brevity_ru(t):
    n = len(ru_tokens(t))
    lo, hi = RU["brevity_ru"]["low"], RU["brevity_ru"]["high"]
    if n == 0: return 0
    if lo <= n <= hi: return 100
    if n < lo: return max(30, 100 - (lo - n) * 11)
    return max(10, 100 - (n - hi) * 7)

PROPS_RU = [("SPECIFICITY", specificity_ru), ("ADDRESS", address_ru), ("STAKES", stakes_ru),
            ("CURIOSITY", curiosity_ru), ("BREVITY", brevity_ru)]

def classify(t, code="en"):
    key, name_key = ("match_ru", "name_ru") if code == "ru" else ("match", "name")
    best, hits = None, 0
    for f in FORMULAS:
        n = sum(1 for p in f.get(key, []) if re.search(p, t, re.I))
        if n > hits: best, hits = f, n
    if not best:
        return ("Без формулы" if code == "ru" else "Unclassified"), 0
    return best.get(name_key, best["name"]), hits

def score(t, code="en"):
    parts = {n: fn(t) for n, fn in (PROPS_RU if code == "ru" else PROPS)}
    vals = list(parts.values())
    verdict = round(0.6 * (sum(vals) / len(vals)) + 0.4 * min(vals))
    name, hits = classify(t, code)
    return parts, verdict, name, hits

def band(v): return "STRONG" if v >= 72 else "WORKABLE" if v >= 55 else "WEAK"

BAND_RU = {"STRONG": "СИЛЬНЫЙ", "WORKABLE": "РАБОЧИЙ", "WEAK": "СЛАБЫЙ"}
PROP_RU = {"SPECIFICITY": "КОНКРЕТИКА", "ADDRESS": "ОБРАЩЕНИЕ", "STAKES": "СТАВКИ",
           "CURIOSITY": "ЛЮБОПЫТСТВО", "BREVITY": "КРАТКОСТЬ"}

def report(t, parts, verdict, name, hits, code="en"):
    if code == "ru":
        return report_ru(t, parts, verdict, name, hits)
    print(f"\n  {t.strip()}")
    print(f"  {'-' * min(72, max(20, len(t.strip())))}")
    for k, v in parts.items():
        print(f"    {k:<12} {v:3d}  {'#' * (v // 5)}")
    print(f"    {'VERDICT':<12} {verdict:3d}  {band(verdict)}")
    print(f"    formula      {name}" + (f"  ({hits} pattern{'s' if hits != 1 else ''} matched)" if hits else "  (no formula matched - that is usually a summary, not a hook)"))
    low = min(parts, key=parts.get)
    print(f"    weakest      {low} - {FIX[low]}")

def report_ru(t, parts, verdict, name, hits):
    print(f"\n  {t.strip()}")
    print(f"  {'-' * min(72, max(20, len(t.strip())))}")
    for k, v in parts.items():
        print(f"    {PROP_RU[k]:<13} {v:3d}  {'#' * (v // 5)}")
    print(f"    {'ИТОГ':<13} {verdict:3d}  {BAND_RU[band(verdict)]}")
    print(f"    формула       {name}" + (f"  (совпало шаблонов: {hits})" if hits else
                                         "  (ни одна формула не подошла: обычно это пересказ, а не хук)"))
    low = min(parts, key=parts.get)
    fix = RU["fix_ru"][low].format(**RU["brevity_ru"])
    print(f"    слабое место  {PROP_RU[low].lower()}: {fix}")

FIX = {
 "SPECIFICITY": "swap one adjective for a number, a name or a date",
 "ADDRESS": "say 'you' in the first six words",
 "STAKES": "name what it costs them to keep doing it the current way",
 "CURIOSITY": "cut the half of the sentence that answers itself",
 "BREVITY": "9 to 24 words. Read it out loud and stop where you run out of breath",
}

def main():
    lang.setup_output()
    a = sys.argv[1:]
    choice, a = lang.take_lang_flag(a)
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if "--hook" in a:
        lines = [a[a.index("--hook") + 1]]
    elif a and os.path.exists(a[0]):
        lines = [l for l in lang.read_text(a[0]).splitlines() if l.strip()]
    else:
        print(__doc__); sys.exit(1 if not a else 0)
    out = []
    for t in lines:
        code = lang.resolve(choice, t)
        parts, verdict, name, hits = score(t, code)
        out.append({"hook": t.strip(), "properties": parts, "verdict": verdict,
                    "band": band(verdict), "formula": name, "matched": hits, "lang": code})
    out.sort(key=lambda r: -r["verdict"])
    if as_json:
        print(json.dumps([{k: v for k, v in r.items() if k != "matched"} for r in out], indent=1, ensure_ascii=False)); return
    for r in out:
        report(r["hook"], r["properties"], r["verdict"], r["formula"], r["matched"], r["lang"])
    if len(out) > 1:
        w = out[0]
        if w["lang"] == "ru":
            print(f"\n  лучший: {w['hook'].strip()}  ({w['verdict']}, {BAND_RU[w['band']]})")
            print("  Оценка отсеивает слабые начала и подсказывает, что исправить. Просмотры она не предсказывает.\n")
        else:
            print(f"\n  winner: {w['hook'].strip()}  ({w['verdict']}, {w['band']})\n")

if __name__ == "__main__":
    main()
