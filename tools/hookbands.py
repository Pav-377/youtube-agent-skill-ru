#!/usr/bin/env python3
"""hookbands.py - fit the Russian «weak» cut of hookscore.py on one half of a labelled set and check
it on data the fit never saw (the owner's protocol of 2026-10-02).

    python tools/hookbands.py

1. tests/fixtures/hooks_ru.json is split in two halves, stratified: within each label, hooks go
   to A and B in turn, in file order.
2. The cut is fitted on A only: «weak» means score < cut. Every whole cut is tried; among those
   with the most right labels on A the middle one is taken (of two, the upper one).
3. The cut is then applied, unchanged, to half B and to tests/fixtures/hooks_ru_holdout.json
   (20 hooks written and committed before they were scored).
4. Accepted only if each of the two held-out sets gets at least 90% right labels. A label is
   right when a weak hook is called weak and an ordinary one is not.

Exit code 0 when accepted, 1 when not. Nothing is written; the cut goes to shared/hookscore.json
by hand.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))
import hookscore as hs  # noqa: E402
import lang  # noqa: E402

NEED = 0.90


def load(name):
    with open(os.path.join(ROOT, "tests", "fixtures", name), encoding="utf-8") as fh:
        return json.load(fh)["hooks"]


def split(hooks):
    a, b, seen = [], [], {}
    for h in hooks:
        n = seen.get(h["label"], 0)
        seen[h["label"]] = n + 1
        (a if n % 2 == 0 else b).append(h)
    return a, b


def scored(hooks):
    return [(hs.score(h["text"], "ru")[1], h["label"] == "weak") for h in hooks]


def right(data, cut):
    return sum((s < cut) == weak for s, weak in data)


def fit(data):
    cuts = range(0, 102)
    best = max(right(data, c) for c in cuts)
    top = [c for c in cuts if right(data, c) == best]
    return top[len(top) // 2], best, (top[0], top[-1])


def main():
    lang.setup_output()
    a, b = split(load("hooks_ru.json"))
    fa = scored(a)
    cut, ok, plateau = fit(fa)
    print(f"  fit on half A ({len(a)} hooks): cut {cut} (cuts {plateau[0]}..{plateau[1]} all give "
          f"{ok}/{len(a)} = {ok / len(a):.0%})")
    passed = True
    for name, data in (("half B", scored(b)), ("20 new hooks", scored(load("hooks_ru_holdout.json")))):
        r = right(data, cut)
        miss = sorted(s for s, weak in data if (s < cut) != weak)
        passed &= r / len(data) >= NEED
        print(f"  {name:<13} {r}/{len(data)} = {r / len(data):.0%} right"
              + (f"; wrong at scores {miss}" if miss else ""))
    print(f"  {'ACCEPTED' if passed else 'REJECTED'} (need at least {NEED:.0%} on each held-out set)")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
