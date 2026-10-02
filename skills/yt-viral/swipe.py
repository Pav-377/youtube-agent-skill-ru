#!/usr/bin/env python3
"""swipe.py - rank collected videos by how far each beat its OWN channel, then name the formula.

    python3 swipe.py collected.json
    python3 swipe.py collected.json --min 2.0 --json

Input is a list you collected - one object per video:

    [{"channel":"Some Channel","title":"...","views":412000,"url":"...","duration":613}, ...]

Raw view counts rank channel size, not ideas. A 400k video on a 2M-subscriber channel is a normal
Tuesday; a 400k video on a channel whose median is 30k is the thing worth studying. So every video
is scored as a MULTIPLE OF ITS OWN CHANNEL'S MEDIAN, which needs at least four videos per channel
to mean anything - the tool says so rather than quietly ranking on noise.

The formula comes from hooks.json (a copy of shared/hooks.json in this folder), matched against the TITLE. It is a judgement
about the words on screen, not a claim about why the video worked.
"""
import json, os, re, statistics, sys

import lang

HERE = os.path.dirname(os.path.abspath(__file__))
FORMULAS = lang.read_json(os.path.join(HERE, "hooks.json"))["hooks"]
CFG = lang.read_json(os.path.join(HERE, "swipe.json"))
SUFFIX = re.compile(r"^(\d+(?:[.,]\d+)?)\s*([^\d\s.,]+)\.?$")


def views_of(value):
    """A view count as an int, from a number or from text as a page shows it: 412000, "412,000",
    "200 000" (any space), "1,2K", "1.2M", "1,2 тыс.", "3 млн просмотров". None if it is not one."""
    if value is None or value == "":
        return 0  # missing counts as zero, as it always has
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = lang.normalize(str(value)).strip()
    for w in CFG["ignore_words"]:
        s = re.sub(r"\b%s\b\.?" % w, "", s)
    s = re.sub(r"(?<=\d)[\s]+(?=\d)", "", s.strip())  # 200 000 -> 200000
    m = SUFFIX.match(s)
    if m:
        mult = CFG["multipliers"].get(m.group(2).rstrip("."))
        return None if mult is None else int(round(float(m.group(1).replace(",", ".")) * mult))
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", s):
        return int(re.sub(r"[,.]", "", s))  # 412,000 / 412.000: views are whole numbers
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None  # "1,5" with no K/тыс./млн is probably a count with its suffix lost: ask, do not guess

def classify(title, code="en"):
    """The formula a title follows, by the patterns in hooks.json - English or Russian ones."""
    key, name = ("match_ru", "name_ru") if code == "ru" else ("match", "name")
    scored = []
    for f in FORMULAS:
        n = sum(1 for p in f.get(key, []) if re.search(p, title, re.I))
        if n: scored.append((n, f.get(name, f["name"])))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ("Без формулы" if code == "ru" else "Unclassified")

def main():
    lang.setup_output()
    a = sys.argv[1:]
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    lo = lang.flag_value(a, "--min", 1.5, float)
    files = [x for x in a if not x.startswith("--") and not re.match(r"^[\d.]+$", x)]
    if not files or not os.path.exists(files[0]): print(__doc__); sys.exit(1)
    rows = lang.read_json(files[0])
    if isinstance(rows, dict): rows = rows.get("videos", [])
    code = lang.detect(" ".join(str(r.get("title", "")) for r in rows))
    by, bad = {}, []
    for n, r in enumerate(rows, 1):
        views = views_of(r.get("views", 0))
        if views is None:
            bad.append((n, r.get("title", ""), r.get("views")))
            continue  # one unreadable count must not shift its channel's median
        by.setdefault(r.get("channel", "?"), []).append(dict(r, views=views))
    for n, title, value in bad:
        print(f"  video {n} ({str(title)[:40]}): cannot read views {value!r} - write a number, e.g. 12000 or 12K"
              if code == "en" else
              f"  Видео {n} ({str(title)[:40]}): не понял число просмотров {value!r}. "
              "Напишите число, например 12000, 12 тыс. или 1,2 млн. Это видео пропущено.", file=sys.stderr)
    out, thin = [], []
    for ch, vids in by.items():
        views = [float(v["views"]) for v in vids]
        med = statistics.median(views) if views else 0
        if len(vids) < CFG["min_videos_per_channel"]:
            thin.append((ch, len(vids)))
            continue
        for v in vids:
            m = (float(v["views"]) / med) if med else 0
            out.append({"channel": ch, "title": v.get("title", ""), "views": v["views"],
                        "median": int(med), "multiple": round(m, 2),
                        "formula": classify(v.get("title", ""), lang.detect(str(v.get("title", "")))),
                        "url": v.get("url", "")})
    out = [r for r in out if r["multiple"] >= lo]
    out.sort(key=lambda r: -r["multiple"])
    if as_json: print(json.dumps({"outliers": out, "skipped_thin_channels": thin}, indent=1, ensure_ascii=False)); return
    if code == "ru":
        return report_ru(rows, by, lo, out, thin)
    print(f"\n  {len(rows)} videos across {len(by)} channels, outliers at {lo}x or better\n")
    for r in out[:25]:
        print(f"    {r['multiple']:5.2f}x  {r['views']:>9,}  vs {r['median']:>9,} median   {r['channel'][:22]:<22} {r['title'][:52]}")
        print(f"            {r['formula']}")
    if not out: print("    nothing cleared the threshold - collect more per channel or lower --min")
    if thin:
        print(f"\n  skipped {len(thin)} channel(s) with under 4 videos collected - a median off one or")
        print( "  two videos is not a median: " + ", ".join(f"{c} ({n})" for c, n in thin[:6]))
    counts = {}
    for r in out: counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    if counts:
        print("\n  formulas among the outliers")
        for f, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {n:2d}x  {f}")
    print()

def report_ru(rows, by, lo, out, thin):
    def n(x): return f"{x:,}".replace(",", " ")
    def k(x): return f"{x:.2f}".replace(".", ",")
    print(f"\n  видео: {len(rows)}, каналов: {len(by)}, выбросы от {k(lo)}× медианы канала\n")
    for r in out[:25]:
        print(f"    {k(r['multiple']):>5}×  {n(r['views']):>11}  при медиане {n(r['median']):>11}   "
              f"{r['channel'][:22]:<22} {r['title'][:52]}")
        print(f"            {r['formula']}")
    if not out: print("    ни одно видео не прошло порог: соберите больше видео с каждого канала или снизьте --min")
    if thin:
        print(f"\n  пропущено каналов, где меньше {CFG['min_videos_per_channel']} видео: {len(thin)}. "
              "Медиана по одному-двум видео ничего не значит: " + ", ".join(f"{c} ({m})" for c, m in thin[:6]))
    counts = {}
    for r in out: counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    if counts:
        print("\n  формулы у выбросов")
        for f, m in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {m:2d}×  {f}")
    print("\n  Формула — это суждение о словах заголовка, а не объяснение, почему видео выстрелило.\n")


if __name__ == "__main__":
    main()
