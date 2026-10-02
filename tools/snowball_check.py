#!/usr/bin/env python3
"""snowball_check.py - compare shared/lang.py's Russian stemmer with the official Snowball vocabulary.

A one-off development check; nothing here ships in the plugin and nothing here touches the network.
Download the two files yourself, then point this script at them:

    https://raw.githubusercontent.com/snowballstem/snowball-data/main/russian/voc.txt
    https://raw.githubusercontent.com/snowballstem/snowball-data/main/russian/output.txt

    python tools/snowball_check.py voc.txt output.txt
    python tools/snowball_check.py voc.txt output.txt --sample 400 > tests/fixtures/snowball_ru/sample.tsv

Prints the share of words stemmed exactly as the reference does, and every mismatch.
--sample N writes N evenly spaced pairs (plus every word with ё, which needs the ё -> е step) as
the fixture tests/test_lang.py checks on every run.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared"))
import lang  # noqa: E402


def pairs(voc, out):
    with open(voc, encoding="utf-8") as a, open(out, encoding="utf-8") as b:
        return [(w.strip(), s.strip()) for w, s in zip(a, b) if w.strip()]


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        sys.exit(1)
    lang.setup_output()
    ps = pairs(a[0], a[1])
    if "--sample" in a:
        n = int(a[a.index("--sample") + 1])
        yo = [p for p in ps if "ё" in p[0]]
        step = max(1, len(ps) // max(1, n - len(yo)))
        chosen = sorted(set(ps[::step][: n - len(yo)] + yo), key=ps.index)
        print("# Sample of the Snowball Russian test vocabulary: word<TAB>expected stem.")
        print("# Source: https://github.com/snowballstem/snowball-data, russian/voc.txt and russian/output.txt")
        print("# Licence: BSD 3-Clause, see LICENSE in this folder. Made by tools/snowball_check.py --sample.")
        for w, s in chosen:
            print(f"{w}\t{s}")
        return
    bad = [(w, s, lang.stem(w)) for w, s in ps if lang.stem(w) != s]
    print(f"{len(ps) - len(bad)} of {len(ps)} words match ({(len(ps) - len(bad)) / len(ps):.3%})")
    for w, want, got in bad:
        print(f"  {w}: reference {want}, lang.py {got}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
