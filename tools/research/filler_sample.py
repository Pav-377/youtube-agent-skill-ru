#!/usr/bin/env python3
"""filler_sample.py - pull filler-word occurrences out of real transcripts for labelling.

    python tools/research/filler_sample.py      # _private/transcripts/*.vtt -> _private/research/fillers_sample.json

Every occurrence of a word from the brief's lists (5.3: hesitation sounds and filler words) is found
with its context and the pauses around it (from YouTube's word timing). Rare kinds are all kept;
the two common ones, вот and ну, are sampled. The order is shuffled with a fixed seed so labels are
not given in transcript order, and the sample is the same on every run.
"""
import glob, json, os, random, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "shared"))
import lang  # noqa: E402
from transcript import load_words  # noqa: E402

KINDS = ["э", "ээ", "эээ", "эм", "мм", "ммм", "а-а", "м-м", "ну", "короче", "типа", "как бы", "в общем",
         "вот", "значит", "это самое", "так сказать", "собственно", "получается", "на самом деле",
         "в принципе", "реально", "прям"]
SAMPLE = {"вот": 45, "ну": 45}
PER_KIND_MAX = 14
CONTEXT = 9


def occurrences(path):
    words, _ = load_words(path)
    # YouTube's captions now carry punctuation and capitals ("Короче,"): compare bare words
    norm = [re.sub(r"^\W+|\W+$", "", lang.normalize(w.text)) for w in words]
    vid = os.path.basename(path).split(".")[0]
    out = []
    for kind in KINDS:
        parts = kind.split()
        for i in range(len(norm) - len(parts) + 1):
            if norm[i:i + len(parts)] != parts:
                continue
            j = i + len(parts) - 1
            out.append({
                "video": vid, "kind": kind, "start": words[i].start, "end": words[j].end,
                "left": " ".join(w.text for w in words[max(0, i - CONTEXT):i]),
                "word": " ".join(w.text for w in words[i:j + 1]),
                "right": " ".join(w.text for w in words[j + 1:j + 1 + CONTEXT]),
                "pause_before": round(words[i].start - words[i - 1].end, 2) if i else None,
                "pause_after": round(words[j + 1].start - words[j].end, 2) if j + 1 < len(words) else None,
            })
    return out


def main():
    lang.setup_output()
    rnd = random.Random(20261002)
    found = [o for f in sorted(glob.glob(os.path.join(ROOT, "_private", "transcripts", "*.vtt")))
             for o in occurrences(f)]
    chosen = []
    for kind in KINDS:
        items = [o for o in found if o["kind"] == kind]
        rnd.shuffle(items)
        chosen += items[:SAMPLE.get(kind, PER_KIND_MAX)]
    rnd.shuffle(chosen)
    for n, o in enumerate(chosen, 1):
        o["id"] = f"f{n:03d}"
    with open(os.path.join(ROOT, "_private", "research", "fillers_sample.json"), "w", encoding="utf-8") as fh:
        json.dump(chosen, fh, ensure_ascii=False, indent=1)
    print(f"  {len(found)} occurrences in the transcripts, {len(chosen)} in the sample")
    by = {}
    for o in chosen:
        by[o["kind"]] = by.get(o["kind"], 0) + 1
    print("  " + ", ".join(f"{k} {v}" for k, v in by.items()))


if __name__ == "__main__":
    main()
