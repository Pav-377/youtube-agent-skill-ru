#!/usr/bin/env python3
"""select_hooks.py - pick strong and weak videos from _private/research/videos.json.

    python tools/research/select_hooks.py           # writes _private/research/hook_selection.json

The rule is the owner's: strong = at least 2x the channel's median views, weak = under 0.5x, the
middle is not used. Two choices of mine, both against bias:
  - the 5 newest videos of a channel are left out: a video a few days old has low views because
    it is young, not because its hook is weak;
  - at most 8 strong and 8 weak per channel, the most extreme first, so one channel with many
    outliers cannot dominate the set.
A channel needs at least 20 videos after that.
"""
import json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "_private", "research")
SKIP_NEWEST, MIN_VIDEOS, PER_SIDE = 5, 20, 8


def main():
    with open(os.path.join(OUT, "videos.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    sel = {}
    for cid, c in data.items():
        vids = [v for v in c["videos"][SKIP_NEWEST:] if v.get("views")]
        if len(vids) < MIN_VIDEOS:
            print(f"  skip {c['channel']}: {len(vids)} videos")
            continue
        med = statistics.median(v["views"] for v in vids)
        strong = sorted((v for v in vids if v["views"] >= 2 * med), key=lambda v: -v["views"])[:PER_SIDE]
        weak = sorted((v for v in vids if v["views"] < 0.5 * med), key=lambda v: v["views"])[:PER_SIDE]
        sel[cid] = {"channel": c["channel"], "median": med, "videos": len(vids),
                    "strong": [dict(v, multiple=round(v["views"] / med, 2)) for v in strong],
                    "weak": [dict(v, multiple=round(v["views"] / med, 2)) for v in weak]}
        print(f"  {c['channel'][:30]:<30} {len(vids):3d} videos, median {int(med):>8}, "
              f"strong {len(strong)}, weak {len(weak)}")
    with open(os.path.join(OUT, "hook_selection.json"), "w", encoding="utf-8") as fh:
        json.dump(sel, fh, ensure_ascii=False, indent=1)
    print(f"  {len(sel)} channels, {sum(len(c['strong']) for c in sel.values())} strong, "
          f"{sum(len(c['weak']) for c in sel.values())} weak")


if __name__ == "__main__":
    main()
