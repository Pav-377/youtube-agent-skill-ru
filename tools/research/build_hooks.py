#!/usr/bin/env python3
"""build_hooks.py - the real hook set: the first 15 seconds of automatic captions of each selected video.

    python tools/research/build_hooks.py      # -> _private/research/hooks_real.json

Strong and weak come from select_hooks.py (2x and under 0.5x of the channel's median views).
Bracketed captions ([Музыка], [Аплодисменты]) are not speech. A video with fewer than 5 spoken
words in its first 15 seconds is left out: its hook is music or a picture, nothing to score.
Channels found to be outside the niche after inspection are listed in OFF_NICHE and left out.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "shared"))
from transcript import load_words  # noqa: E402

OUT = os.path.join(ROOT, "_private", "research")
SECONDS, MIN_WORDS = 15.0, 5
OFF_NICHE = {"Viliriti"}  # a Brawl Stars gaming channel, not YouTube blogging


def main():
    with open(os.path.join(OUT, "hook_selection.json"), encoding="utf-8") as fh:
        sel = json.load(fh)
    rows, skipped = [], {"off_niche": 0, "no_captions": 0, "too_few_words": 0}
    for c in sel.values():
        for side in ("strong", "weak"):
            for v in c[side]:
                if c["channel"] in OFF_NICHE:
                    skipped["off_niche"] += 1
                    continue
                path = os.path.join(OUT, "subs", v["id"] + ".ru.vtt")
                if not os.path.exists(path):
                    skipped["no_captions"] += 1
                    continue
                words, _ = load_words(path)
                spoken = [w.text for w in words if w.start < SECONDS and not re.match(r"^\[.*\]$", w.text)]
                if len(spoken) < MIN_WORDS:
                    skipped["too_few_words"] += 1
                    continue
                rows.append({"id": v["id"], "channel": c["channel"], "label": side, "multiple": v["multiple"],
                             "title": v["title"], "hook": " ".join(spoken)})
    with open(os.path.join(OUT, "hooks_real.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"  {len(rows)} hooks: {sum(r['label'] == 'strong' for r in rows)} strong, "
          f"{sum(r['label'] == 'weak' for r in rows)} weak, {len({r['channel'] for r in rows})} channels; "
          f"left out: {skipped}")


if __name__ == "__main__":
    main()
