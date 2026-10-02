#!/usr/bin/env python3
"""deadair_ru.py - the Russian edit decision list. Called by deadair.py for a Russian transcript.

What it lists, each with start and end, a decision (CUT / KEEP) and a short reason:
  ПАУЗА     a silence longer than the floor, trimmed from the middle so both sides keep a breath
  ЗАМИНКА   э, ээ, эм, мм - always cut
  ПАРАЗИТ   ну, короче, вот, как бы, типа ... - cut, or kept as live speech (fillers_ru.py)
  ПОВТОР    a phrase started again (the first attempt is cut), or я я / в в

Times are exact when the transcript has a time for every word - YouTube's automatic captions,
whisper with word timestamps. In an .srt only lines are timed, so a word's time is estimated from
the characters before it in its line and shown with ≈.
"""
import json, re

import lang
from fillers_ru import CFG as FILLERS, HESITATION, analyse, bare
from transcript import load_words

KIND = {"dead": "ПАУЗА", "hesitation": "ЗАМИНКА", "filler": "ПАРАЗИТ", "repeat": "ПОВТОР"}
CODE = {"dead": "DEAD", "hesitation": "HESITATION", "filler": "FILLER", "repeat": "REPEAT"}
HINT = ("Время слов приблизительное: в этом файле размечены только строки. Для точного времени "
        "возьмите автосубтитры YouTube (.vtt, например: yt-dlp --write-auto-subs --sub-langs ru "
        "--skip-download ССЫЛКА) или Whisper с пословным временем (--word_timestamps True).")


def words_of(text):
    return [w for w in (bare(t) for t in text.split()) if w]


def only_filler(text):
    """A line that is nothing but hesitations and filler words: not speech for the restart check."""
    ws = words_of(text)
    singles = {p for p in FILLERS["fillers"] if " " not in p}
    return bool(ws) and all(HESITATION.match(w) or w in singles for w in ws)


def restarts(cues):
    """A line whose first 3-5 words repeat the opening of the last line of speech before it:
    the first attempt is the one to cut (as in deadair.py, but on Cyrillic words)."""
    out = []
    for i, (s, e, t) in enumerate(cues):
        if not t.strip() or only_filler(t):
            continue
        j = i - 1
        while j >= 0 and (only_filler(cues[j][2]) or not cues[j][2].strip()):
            j -= 1
        if j < 0:
            continue
        a1, b1 = words_of(cues[j][2])[:5], words_of(t)[:5]
        k = min(len(a1), len(b1))
        if k >= 3 and a1[:k] == b1[:k]:
            out.append({"kind": "repeat", "start": cues[j][0], "end": cues[j][1], "decision": "CUT",
                        "why": "фраза начата заново, первая попытка лишняя", "text": cues[j][2][:60]})
    return out


def pauses(cues, words, exact, floor):
    """Silences longer than the floor: between words when they are timed, else between lines."""
    spans = [(w.start, w.end) for w in words] if exact else [(c[0], c[1]) for c in cues]
    out = []
    for (s0, e0), (s1, _) in zip(spans, spans[1:]):
        gap = s1 - e0
        if gap > floor:
            keep = floor / 2
            out.append({"kind": "dead", "start": round(e0 + keep, 3), "end": round(s1 - keep, 3),
                        "decision": "CUT", "why": f"пауза {gap:.2f} с".replace(".", ","), "text": ""})
    return out


def merged_length(marks):
    spans = sorted((m["start"], m["end"]) for m in marks if m["decision"] == "CUT" and m["end"] > m["start"])
    total, cur = 0.0, None
    for s, e in spans:
        if cur and s <= cur[1]:
            cur[1] = max(cur[1], e)
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = [s, e]
    return total + (cur[1] - cur[0] if cur else 0.0)


def num(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def run(path, cues, floor, as_json):
    words, exact = load_words(path)
    dur = cues[-1][1]
    marks = pauses(cues, words, exact, floor) + analyse(words) + restarts(cues)
    marks = [m for m in marks if m["end"] > m["start"]]
    marks.sort(key=lambda m: (m["start"], m["kind"]))
    removed = merged_length(marks)
    if as_json:
        print(json.dumps({"source": path, "duration": dur, "lang": "ru", "exact_times": exact,
                          "cuts": [dict(m, kind=CODE[m["kind"]], approx=not exact) for m in marks],
                          "removed": round(removed, 3), "out": round(dur - removed, 3)},
                         indent=1, ensure_ascii=False))
        return
    approx = "" if exact else "≈"
    print(f"\n  {path}   {num(dur)} с, реплик: {len(cues)}, слов: {len(words)}, порог паузы {num(floor)} с")
    print(f"  время слов {'точное' if exact else 'приблизительное (≈)'}\n")
    for m in marks:
        text = f"   «{m['text']}»" if m["text"] and m["kind"] != "repeat" else ""
        print(f"    {KIND[m['kind']]:<8} {approx}{num(m['start']):>8} -> {approx}{num(m['end']):>8}  "
              f"{num(m['end'] - m['start']):>5} с   {m['decision']:<4}  {m['why']}{text}")
    cut = [m for m in marks if m["decision"] == "CUT"]
    keep = [m for m in marks if m["decision"] == "KEEP"]
    print(f"\n  вырезать: {len(cut)}, это {num(removed)} с; останется {num(dur - removed)} с "
          f"(короче на {num(removed / dur * 100 if dur else 0, 1)}%)")
    if keep:
        print(f"  оставить как живую речь: {len(keep)}")
    if not exact:
        print(f"\n  {HINT}")
    print()
