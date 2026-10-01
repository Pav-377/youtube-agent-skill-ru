#!/usr/bin/env python3
"""hookeval.py - how well hookscore.py separates strong hooks from weak ones.

    python tools/hookeval.py                                  # English set, ours vs the original
    python tools/hookeval.py --rows                           # also every hook whose score moved
    python tools/hookeval.py --strong a.txt --weak b.txt      # any labelled set, one hook per line

Two numbers per version:
  gap         mean verdict of the strong hooks minus mean verdict of the weak ones
  P(s>w)      share of (strong, weak) pairs where the strong hook scores higher; a tie counts half

The original is unpacked from git commit a2feb21 into a temporary folder, so this needs the git
history but never touches any checkout of the original. Noise threshold agreed with the owner:
a change smaller than 1 point of gap and 2 percentage points of P(s>w) is noise.
"""
import importlib.util, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from golden import golden  # noqa: E402

EN = os.path.join(ROOT, "tests", "fixtures", "en")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(path))  # hookscore.py imports its neighbours
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def lines(path):
    with open(path, encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def stats(scores_strong, scores_weak):
    s, w = scores_strong, scores_weak
    pairs = sum((a > b) + 0.5 * (a == b) for a in s for b in w) / (len(s) * len(w))
    ms, mw = sum(s) / len(s), sum(w) / len(w)
    return {"strong": ms, "weak": mw, "gap": ms - mw, "p": pairs}


def evaluate(mod, strong, weak):
    return [mod.score(t)[1] for t in strong], [mod.score(t)[1] for t in weak]


def main():
    a = sys.argv[1:]
    strong = lines(a[a.index("--strong") + 1] if "--strong" in a else os.path.join(EN, "hooks_en_strong.txt"))
    weak = lines(a[a.index("--weak") + 1] if "--weak" in a else os.path.join(EN, "hooks_en_weak.txt"))
    ours = load_module(os.path.join(ROOT, "skills", "yt-script", "hookscore.py"), "hookscore_ours")
    with tempfile.TemporaryDirectory() as tmp:
        orig = load_module(os.path.join(golden.extract_original(tmp), "yt-script", "hookscore.py"), "hookscore_orig")
        res = {"original": evaluate(orig, strong, weak), "this version": evaluate(ours, strong, weak)}
    print(f"\n  {len(strong)} strong, {len(weak)} weak hooks\n")
    print(f"  {'version':<14} {'strong':>7} {'weak':>7} {'gap':>6} {'P(s>w)':>7}")
    st = {k: stats(*v) for k, v in res.items()}
    for k, v in st.items():
        print(f"  {k:<14} {v['strong']:7.1f} {v['weak']:7.1f} {v['gap']:6.1f} {v['p']:7.3f}")
    d_gap = st["this version"]["gap"] - st["original"]["gap"]
    d_p = (st["this version"]["p"] - st["original"]["p"]) * 100
    noise = d_gap > -1 and d_p > -2
    print(f"\n  change: gap {d_gap:+.1f}, P(s>w) {d_p:+.1f} pp -> "
          f"{'not worse beyond noise' if noise else 'WORSE than the noise threshold'}")
    if "--rows" in a:
        texts = [("S", t) for t in strong] + [("W", t) for t in weak]
        before = res["original"][0] + res["original"][1]
        after = res["this version"][0] + res["this version"][1]
        print("\n  hooks whose score changed:")
        for (lab, t), b, n in zip(texts, before, after):
            if b != n:
                print(f"    {lab} {b:3d} -> {n:3d}  {t[:72]}")
    print()
    sys.exit(0 if noise else 1)


if __name__ == "__main__":
    main()
