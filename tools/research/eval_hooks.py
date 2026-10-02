#!/usr/bin/env python3
"""eval_hooks.py - the brief's numbers for the Russian hook scorer (5.2).

    python tools/research/eval_hooks.py [--band LOW HIGH]

Three sets:
  real       _private/research/hooks_real.json - first 15 s of automatic captions, labelled by
             views (2x / under 0.5x of the channel median). Priority: real data.
  synthetic  tests/fixtures/hooks_ru.json - 51 hooks written for the project, labelled by judgement.
  pairs      the 26 Russian/English pairs from the same file.
For each: strong mean, weak mean, gap (brief: >= 20), P(strong > weak); for pairs, the share with
|ru - en| <= 10 (brief: >= 80%). --band overrides the Russian brevity band for an experiment.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "skills", "yt-script"))
import hookscore as hs  # noqa: E402


def stats(strong, weak):
    s, w = [hs.score(t, "ru")[1] for t in strong], [hs.score(t, "ru")[1] for t in weak]
    pairs = sum((a > b) + 0.5 * (a == b) for a in s for b in w) / (len(s) * len(w))
    return {"n": (len(s), len(w)), "strong": sum(s) / len(s), "weak": sum(w) / len(w),
            "gap": sum(s) / len(s) - sum(w) / len(w), "p": pairs}


def evaluate():
    out = {}
    real = os.path.join(ROOT, "_private", "research", "hooks_real.json")
    if os.path.exists(real):
        with open(real, encoding="utf-8") as fh:
            d = json.load(fh)
        out["real"] = stats([r["hook"] for r in d if r["label"] == "strong"],
                            [r["hook"] for r in d if r["label"] == "weak"])
    with open(os.path.join(ROOT, "tests", "fixtures", "hooks_ru.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    out["synthetic"] = stats([h["text"] for h in doc["hooks"] if h["label"] == "strong"],
                             [h["text"] for h in doc["hooks"] if h["label"] == "weak"])
    diffs = [abs(hs.score(p["ru"], "ru")[1] - hs.score(p["en"], "en")[1]) for p in doc["pairs"]]
    out["pairs"] = {"n": len(diffs), "within_10": sum(d <= 10 for d in diffs) / len(diffs),
                    "mean_abs_diff": sum(diffs) / len(diffs)}
    return out


def main():
    hs.lang.setup_output()
    a = sys.argv[1:]
    if "--band" in a:
        i = a.index("--band")
        hs.RU["brevity_ru"]["low"], hs.RU["brevity_ru"]["high"] = int(a[i + 1]), int(a[i + 2])
    r = evaluate()
    for k in ("real", "synthetic"):
        if k in r:
            v = r[k]
            print(f"  {k:<10} n={v['n'][0]}/{v['n'][1]}  strong {v['strong']:5.1f}  weak {v['weak']:5.1f}  "
                  f"gap {v['gap']:5.1f} (>=20)  P(s>w) {v['p']:.3f}")
    p = r["pairs"]
    print(f"  pairs      n={p['n']}  |ru-en|<=10: {p['within_10']:.0%} (>=80%)  mean |diff| {p['mean_abs_diff']:.1f}")


if __name__ == "__main__":
    main()
