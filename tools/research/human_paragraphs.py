#!/usr/bin/env python3
"""human_paragraphs.py - paragraphs of real Russian speech for the AI-tell check (brief 5.7).

    python tools/research/human_paragraphs.py    # -> _private/research/human_paragraphs.json

Taken from the transcripts in _private/transcripts that YouTube punctuated (the others are one
endless sentence and say nothing about sentence length). Four consecutive sentences make a
paragraph; PER_VIDEO paragraphs are spaced evenly through each video. The text is third-party
speech, so the result stays in _private/ and the acceptance test that reads it is skipped in CI.

A second, supplementary set: the first 15 seconds of the real hooks (hooks_real.json) that carry
punctuation. Supplementary because in an AI niche some of those intros may themselves be
machine-written.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "shared"))
from transcript import load_words  # noqa: E402

OUT = os.path.join(ROOT, "_private", "research")
PER_VIDEO, SENTENCES = 20, 4


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if len(s.split()) >= 2]


def main():
    paras = []
    for f in sorted(glob.glob(os.path.join(ROOT, "_private", "transcripts", "*.vtt"))):
        words, _ = load_words(f)
        text = " ".join(w.text for w in words if not re.match(r"^\[.*\]$", w.text))
        sents = sentences(text)
        if len(sents) < 100:
            continue  # unpunctuated captions
        blocks = [sents[i:i + SENTENCES] for i in range(0, len(sents) - SENTENCES, SENTENCES)]
        step = max(1, len(blocks) // PER_VIDEO)
        vid = os.path.basename(f).split(".")[0]
        paras += [{"source": vid, "text": " ".join(b)} for b in blocks[::step][:PER_VIDEO]]
    hooks = []
    real = os.path.join(OUT, "hooks_real.json")
    if os.path.exists(real):
        with open(real, encoding="utf-8") as fh:
            for r in json.load(fh):
                if len(re.findall(r"[.!?]", r["hook"])) >= 2:
                    hooks.append({"source": r["channel"], "text": r["hook"]})
    with open(os.path.join(OUT, "human_paragraphs.json"), "w", encoding="utf-8") as fh:
        json.dump({"speech": paras, "hooks": hooks}, fh, ensure_ascii=False, indent=1)
    print(f"  {len(paras)} speech paragraphs from {len({p['source'] for p in paras})} videos, "
          f"{len(hooks)} punctuated hooks from {len({h['source'] for h in hooks})} channels")


if __name__ == "__main__":
    main()
