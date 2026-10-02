#!/usr/bin/env python3
"""eval_fillers.py - score skills/yt-edit/fillers_ru.py against the labelled real transcripts.

    python tools/research/eval_fillers.py [--rows]

Needs _private/transcripts/*.vtt and _private/research/fillers_gold.json (tools/research/
filler_sample.py, then two labelling passes). Prints the brief's acceptance numbers (5.3):
  precision of CUT       share of the tool's CUT marks on labelled words that should be cut (>= 90%)
  hesitation recall      share of labelled hesitations the tool cuts (>= 95%)
  meaning hits           labelled meaningful uses the tool marked at all (must be 0)
and, for information, filler recall: how many of the fillers that should go it finds.
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "skills", "yt-edit"))
import lang  # noqa: E402
from fillers_ru import analyse  # noqa: E402
from transcript import load_words  # noqa: E402


def marks_by_video():
    out = {}
    for f in glob.glob(os.path.join(ROOT, "_private", "transcripts", "*.vtt")):
        words, _ = load_words(f)
        out[os.path.basename(f).split(".")[0]] = analyse(words)
    return out


def evaluate(show_rows=False):
    with open(os.path.join(ROOT, "_private", "research", "fillers_gold.json"), encoding="utf-8") as fh:
        gold = json.load(fh)
    marks = marks_by_video()
    tool_cut = good_cut = h_total = h_cut = m_hits = c_total = c_cut = 0
    rows = []
    for g in gold:
        hit = [m for m in marks.get(g["video"], []) if abs(m["start"] - g["start"]) < 0.02]
        dec = hit[0]["decision"] if hit else "-"
        if dec == "CUT":
            tool_cut += 1
            good_cut += g["gold"] in "CH"
        h_total += g["gold"] == "H"
        h_cut += g["gold"] == "H" and dec == "CUT"
        c_total += g["gold"] == "C"
        c_cut += g["gold"] == "C" and dec == "CUT"
        m_hits += g["gold"] == "M" and bool(hit)
        bad = (dec == "CUT" and g["gold"] not in "CH") or (g["gold"] == "M" and hit) or (g["gold"] == "H" and dec != "CUT")
        rows.append((bad, g, dec, hit[0]["why"] if hit else ""))
    res = {"items": len(gold), "tool_cut": tool_cut, "precision": good_cut / tool_cut if tool_cut else 1.0,
           "hesitation_recall": h_cut / h_total if h_total else 1.0, "meaning_hits": m_hits,
           "filler_recall": c_cut / c_total if c_total else 1.0, "hesitations": h_total}
    if show_rows:
        for bad, g, dec, why in rows:
            if bad:
                print(f"  {g['id']} gold {g['gold']} tool {dec:<4} {g['left'][-40:]} [[{g['word']}]] {g['right'][:40]}  ({why})")
    return res


def main():
    lang.setup_output()
    r = evaluate("--rows" in sys.argv)
    print(f"\n  {r['items']} labelled words, tool cuts {r['tool_cut']} of them")
    print(f"  precision of CUT     {r['precision']:.1%}   (brief: >= 90%)")
    print(f"  hesitation recall    {r['hesitation_recall']:.1%}   of {r['hesitations']} (brief: >= 95%)")
    print(f"  meaning hits         {r['meaning_hits']}        (brief: 0)")
    print(f"  filler recall        {r['filler_recall']:.1%}   (information)\n")


if __name__ == "__main__":
    main()
