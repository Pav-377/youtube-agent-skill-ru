#!/usr/bin/env python3
"""fillers_ru.py - Russian hesitations, filler words and stumbles, word by word (brief 5.3).

    from fillers_ru import analyse
    marks = analyse(words)    # words from transcript.load_words(); returns a list of dicts

Three kinds of marks, each with a time span, a decision and a short reason in Russian:
  hesitation   э, ээ, эм, мм ...                      always CUT
  filler       ну, короче, вот, как бы, типа ...      CUT or KEEP by context
  repeat       я я, в в - a function word twice       CUT (ужас ужас is emphasis and stays)

The rule of the whole module: cutting a word the speaker meant is worse than leaving a filler in.
So a word that often carries meaning (реально, прям, на самом деле) is never cut automatically,
and вот, значит, типа, получается are cut only where their filler use is unmistakable. A word used
for its meaning (вот этот файл, это значит, типа снежок, у меня получается) gets no mark at all.
Every list and threshold is in fillers.json.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "fillers.json"), encoding="utf-8") as _fh:
    CFG = json.load(_fh)
G = CFG["guards"]
HESITATION = re.compile(CFG["hesitation_regex"])
PAUSE = CFG["pause_seconds"]
SENTENCE_END = (".", "!", "?", "…", ":")
VERBISH = re.compile(r"(ть|ться|ешь|ишь|ет|ит|ют|ят|ете|ите|ся|сь)$")
PAST = re.compile(r"(ал|ала|али|ало|ил|ила|или|ило|ул|ула|ули|ел|ела|ели|ыл|ыла|ыли)$")
NUMBERS = ("один", "одна", "два", "две", "три", "четыре", "пять", "десять", "сто")


def verbish(w):
    """Looks like a verb: present/infinitive endings, or a past ending on a word long enough to be
    one (боул, стул, мел are not verbs)."""
    return bool(VERBISH.search(w)) or (len(w) >= 5 and bool(PAST.search(w)))


def bare(text):
    return re.sub(r"^\W+|\W+$", "", text.lower().replace("ё", "е"))


class Token:
    __slots__ = ("start", "end", "text", "w", "i")

    def __init__(self, i, word):
        self.i, self.start, self.end, self.text = i, word.start, word.end, word.text
        self.w = bare(word.text)


def _phrases():
    return sorted(CFG["fillers"], key=lambda p: -len(p.split()))


def analyse(words):
    toks = [Token(i, w) for i, w in enumerate(words)]
    toks = [t for t in toks if t.w]  # [музыка] and stray punctuation are not words
    n = len(toks)

    def gap_before(k):
        return toks[k].start - toks[k - 1].end if k > 0 else 99.0

    def gap_after(k):
        return toks[k + 1].start - toks[k].end if k + 1 < n else 99.0

    def word(k):
        return toks[k].w if 0 <= k < n else ""

    def starts_phrase(k):
        if k == 0 or gap_before(k) >= PAUSE:
            return True
        prev = toks[k - 1].text.rstrip()
        return prev.endswith(SENTENCE_END) or (toks[k].text[:1].isupper() and toks[k].w != "я")

    # 1. find candidates: hesitations, then the longest filler phrase at each position
    cands = []
    k = 0
    while k < n:
        if HESITATION.match(toks[k].w):
            cands.append({"kind": "hesitation", "a": k, "b": k, "phrase": toks[k].w})
            k += 1
            continue
        for p in _phrases():
            parts = p.split()
            if [word(k + j) for j in range(len(parts))] == parts:
                cands.append({"kind": "filler", "a": k, "b": k + len(parts) - 1, "phrase": p})
                k += len(parts)
                break
        else:
            k += 1

    def is_meaningful(c):
        """True when the word is used for what it means: no mark at all."""
        p, a, b = c["phrase"], c["a"], c["b"]
        prev, nxt = word(a - 1), word(b + 1)
        if prev in G["speech_verbs"] and p in ("ну", "типа", "короче", "вот"):
            return True  # the start of a quote
        if prev in G["interjections"] or nxt in G["interjections"]:
            return True  # part of an exclamation: вау, ну, вау
        if p == "вот":
            after = word(b + 2)
            ну_вот = prev == "ну" and not _punct(toks[a - 1].text) and not _punct(toks[a].text)
            return (nxt in G["вот_next"] or prev in G["вот_prev"] or ну_вот
                    or nxt[:1].isdigit() or nxt in NUMBERS or after[:1].isdigit() or after in NUMBERS)
        if p == "ну":
            ну_вот = nxt == "вот" and b + 1 < n and not _punct(toks[b].text) and not _punct(toks[b + 1].text)
            return nxt in G["ну_idioms_next"] or ну_вот
        if p == "значит":
            return toks[b].text.rstrip().endswith(SENTENCE_END)  # что он значит. - the verb
        if p == "типа":
            return prev in G["типа_prev_meaning"]  # это типа боул - a comparison
        if p == "как бы":
            return nxt in G["как_бы_next_pronouns"]
        if p == "в принципе":
            return prev in G["в_принципе_prev"]
        if p == "собственно":
            return nxt in G["собственно_next"]
        if p == "в общем":
            return nxt in G["в_общем_next"]
        if p == "короче":
            return prev in G["короче_prev"] or nxt in G["короче_next"]
        return False

    # 2. decide, left to right, so a stack knows what came before it
    marks, prev_cand_end = [], None
    for c in cands:
        a, b = c["a"], c["b"]
        span = (toks[a].start, toks[b].end)
        stacked = prev_cand_end is not None and prev_cand_end == a - 1 and gap_before(a) < PAUSE
        if c["kind"] == "hesitation":
            marks.append(_mark("hesitation", span, "CUT", "звук-заминка", toks[a].text))
            prev_cand_end = b
            continue
        rule = CFG["fillers"][c["phrase"]]
        if rule["inside"] == "never" or is_meaningful(c):
            prev_cand_end = None if rule["inside"] == "never" else prev_cand_end
            continue
        alone = gap_before(a) >= PAUSE and gap_after(b) >= PAUSE
        at_start = starts_phrase(a) or word(b + 1) in G["phrase_openers"]
        decision = reason = None
        if alone:
            decision, reason = "CUT", "стоит отдельно в паузе"
        elif stacked:
            decision, reason = "CUT", "несколько паразитов подряд"
        elif at_start:
            if rule["keep_at_start"]:
                decision, reason = "KEEP", "связка в начале фразы, живая речь"
        else:
            decision, reason = _inside(rule["inside"], c, word, toks)
        if decision:
            marks.append(_mark("filler", span, decision, reason, " ".join(toks[j].text for j in range(a, b + 1))))
            prev_cand_end = b
        else:
            prev_cand_end = None

    # 3. a function word said twice in a row is a stumble
    fw = set(CFG["repeat"]["function_words"])
    for k in range(1, n):
        if toks[k].w == toks[k - 1].w and toks[k].w in fw and gap_before(k) < 1.0:
            marks.append(_mark("repeat", (toks[k - 1].start, toks[k - 1].end), "CUT",
                               f"слово «{toks[k].w}» сказано дважды", toks[k - 1].text))

    # 4. density: too many fillers in a short stretch and the kept connectors go too
    dens = CFG["density"]
    fill = [m for m in marks if m["kind"] == "filler"]
    for m in fill:
        if m["decision"] != "KEEP":
            continue
        near = sum(1 for x in fill if abs(x["start"] - m["start"]) <= dens["window_seconds"] / 2)
        if near > dens["max_fillers"]:
            m["decision"], m["why"] = "CUT", f"слишком часто: {near} паразитов за {dens['window_seconds']} с"
    marks.sort(key=lambda m: m["start"])
    return marks


def _inside(how, c, word, toks):
    a, b = c["a"], c["b"]
    prev, nxt = word(a - 1), word(b + 1)
    if how == "cut":
        return "CUT", "паразит внутри фразы, смысл не меняется"
    if how == "cut_before_verb":
        if nxt in G["типа_next_ok"] or verbish(nxt):
            return "CUT", "паразит внутри фразы, смысл не меняется"
    if how == "cut_narrative":
        between_commas = toks[a - 1].text.endswith(",") and toks[b].text.endswith(",") if a > 0 else False
        if between_commas or (prev in G["значит_subjects"] and nxt not in G["значит_not_next"]):
            return "CUT", "паразит внутри фразы, смысл не меняется"
    if how == "cut_after_и":
        if prev == "и" and nxt not in G["получается_not_next"]:
            return "CUT", "паразит внутри фразы, смысл не меняется"
    return None, None


def _punct(text):
    return bool(re.search(r"[,.!?:;…]$", text.strip()))


def _mark(kind, span, decision, why, text):
    return {"kind": kind, "start": round(span[0], 3), "end": round(span[1], 3), "decision": decision,
            "why": why, "text": text}
