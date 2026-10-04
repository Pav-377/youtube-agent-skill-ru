#!/usr/bin/env python3
"""deadair.py - an edit decision list from a timestamped transcript.

    python3 deadair.py transcript.srt            # or .vtt, or whisper .json
    python3 deadair.py transcript.srt --floor 0.35 --json

Finds three things and prints the cuts as a list you can act on, newest problem first:
  DEAD    gaps between spoken cues longer than the floor
  FILLER  cues that are only filler ("um", "so yeah", "basically")
  REPEAT  a sentence restarted - the second take of the same opening

A Russian transcript (detected, or --lang ru) gets the Russian edit list from deadair_ru.py: word by
word, hesitations always cut, filler words cut or kept by context with a reason for each, and the
times exact when the transcript has them per word (YouTube's automatic captions, whisper with word
timestamps) and marked with ≈ when they are estimated (.srt).

WHAT IT DOES NOT DO. It does not cut the file. It prints an EDL, the total it would remove, and the
runtime you would land on, and you apply it in whatever editor you use. Nothing here touches media.
"""
import json, os, re, sys

import lang

FILLER_ONLY = re.compile(r"^[\s,.-]*((um+|uh+|er+|ah+|so|okay|ok|right|yeah|like|anyway|basically|"
                         r"actually|you know|i mean|let me see|hold on)[\s,.-]*)+$", re.I)

from transcript import load, parse_ts  # noqa: E402,F401  (one parser for every skill)

def norm(t): return re.sub(r"[^a-z ]", "", t.lower()).split()

USAGE_RU = """deadair.py — монтажный лист по транскрипту с таймкодами.

    python3 deadair.py транскрипт.vtt                   # или .srt, или .json от Whisper
    python3 deadair.py транскрипт.vtt --floor 0.35      # порог паузы в секундах
    python3 deadair.py транскрипт.vtt --json            # вывод в JSON
    python3 deadair.py транскрипт.vtt --lang ru         # язык: ru, en или auto (по умолчанию)

Скрипт не режет видео. Он выводит список того, что вырезать и что оставить.
"""


def main():
    lang.setup_output()
    a = sys.argv[1:]
    choice, a = lang.take_lang_flag(a)
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    floor = lang.flag_value(a, "--floor", 0.45, float)
    a = [x for x in a if not x.startswith("--") and not re.match(r"^[\d.]+$", x)]
    if not a or not os.path.exists(a[0]): lang.usage(__doc__, USAGE_RU, choice, missing=a[0] if a else None)
    cues = load(a[0])
    if not cues:
        print("no cues found - is this an srt, vtt or whisper json?" if lang.ui_lang(choice) == "en" else
              "В файле нет реплик с таймкодами. Нужен транскрипт .srt, .vtt или .json от Whisper.")
        sys.exit(1)
    if lang.resolve(choice, " ".join(c[2] for c in cues[:200])) == "ru":
        from deadair_ru import run
        return run(a[0], cues, floor, as_json)
    dur = cues[-1][1]
    cuts = []
    for i, (s, e, t) in enumerate(cues):
        if FILLER_ONLY.match(t):
            cuts.append({"kind": "FILLER", "start": s, "end": e, "why": t.strip()[:48]})
        if i:
            gap = s - cues[i - 1][1]
            if gap > floor:
                keep = floor / 2
                cuts.append({"kind": "DEAD", "start": round(cues[i - 1][1] + keep, 3),
                             "end": round(s - keep, 3), "why": f"{gap:.2f}s gap"})
        # A restart is compared against the last cue that was actually SPEECH. Comparing against
        # the literal previous cue misses every retake with an "um" between the two attempts, which
        # is most of them.
        if t.strip() and not FILLER_ONLY.match(t):
            j = i - 1
            while j >= 0 and (FILLER_ONLY.match(cues[j][2]) or not cues[j][2].strip()): j -= 1
            if j >= 0:
                a1, b1 = norm(cues[j][2])[:5], norm(t)[:5]
                if len(a1) >= 3 and a1 == b1:
                    cuts.append({"kind": "REPEAT", "start": cues[j][0], "end": cues[j][1],
                                 "why": f'restart of "{" ".join(a1)}"'})
    cuts = [c for c in cuts if c["end"] > c["start"]]
    cuts.sort(key=lambda c: c["start"])
    removed = sum(c["end"] - c["start"] for c in cuts)
    if as_json:
        print(json.dumps({"source": a[0], "duration": dur, "cuts": cuts,
                          "removed": round(removed, 3), "out": round(dur - removed, 3)}, indent=1, ensure_ascii=False)); return
    print(f"\n  {a[0]}   {dur:.2f}s in, {len(cues)} cues, dead-air floor {floor}s\n")
    for c in cuts:
        print(f"    {c['kind']:<7} {c['start']:8.2f} -> {c['end']:8.2f}   {c['end']-c['start']:5.2f}s   {c['why']}")
    print(f"\n  {len(cuts)} cuts, {removed:.2f}s removed, {dur - removed:.2f}s out "
          f"({removed / dur * 100:.1f}% shorter)\n")

if __name__ == "__main__":
    main()
