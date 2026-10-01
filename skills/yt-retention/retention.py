#!/usr/bin/env python3
"""retention.py - read a YouTube Studio audience-retention export and find the leaks.

    python3 retention.py retention.csv
    python3 retention.py retention.csv --transcript transcript.srt   # names what was said at each drop
    python3 retention.py retention.csv --duration 600                # seconds for a percentage axis
    python3 retention.py export.zip                                  # the archive Studio downloads
    python3 retention.py retention.csv --json
    python3 retention.py retention.csv --lang ru                     # report language: ru, en or auto

Get the file from Studio: Analytics -> a video -> Engagement -> the audience-retention chart ->
the download icon -> "Audience retention". Two columns, a position (percent or seconds) and a
percentage still watching.

Any locale reads: comma, semicolon or tab between columns; 80,5 and 80.5; 1 234 with an ordinary,
non-breaking or narrow space; 0.8 as well as 80%; 0:47, 00:00:47 and 1:02:03; Russian or English
headers; UTF-8, UTF-16 or cp1251. The report comes out in the language of the file.

It reports three things, because they are three different problems with three different fixes:
  HOOK LEAK    what you lost in the first 30 seconds
  CLIFFS       single steep drops - a specific moment people left at
  SLIDE        the steady bleed rate across the flat middle

With --transcript it prints what you were saying at each cliff, which is the only version of this
report you can act on without scrubbing the video yourself. On a percentage axis it takes the
video's length from the end of the transcript unless --duration says otherwise.
"""
import csv, io, json, os, re, sys, zipfile

import lang

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = lang.read_json(os.path.join(HERE, "retention.json"))

MSG = {
    "missing": {"en": "no such file: {path}",
                "ru": "Файл не найден: {path}. Проверьте путь и имя файла."},
    "few_points": {"en": "could not read at least {n} data points from that csv",
                   "ru": "В файле меньше {n} точек графика, так что это не похоже на выгрузку удержания. "
                         "Нужен файл графика «Удержание аудитории» из YouTube Studio."},
    "zip_none": {"en": "{path} holds no retention table. Files inside: {files}. "
                       "Pass the CSV with the retention chart, or the archive Studio downloads for it.",
                 "ru": "В архиве {path} нет таблицы удержания. Файлы внутри: {files}. "
                       "Передайте CSV с графиком удержания или архив, который Studio скачивает для него."},
    "no_transcript": {"en": "no such transcript: {path}",
                      "ru": "Транскрипт не найден: {path}. Проверьте путь или запустите без --transcript."},
    "bad_duration": {"en": "--duration needs the video length in seconds, for example --duration 600",
                     "ru": "После --duration нужна длина ролика в секундах, например --duration 600"},
}


class Problem(Exception):
    def __init__(self, key, **kw):
        super().__init__(key)
        self.key, self.kw = key, kw

    def text(self, code):
        return MSG[self.key][code].format(**self.kw)


# --- reading numbers in any locale ----------------------------------------------------------------
SPACES = re.compile(r"[\s    ]+")
TIME = re.compile(r"^(\d+):(\d{1,2})(?::(\d{1,2}(?:[.,]\d+)?))?$")


def bare(cell):
    return SPACES.sub("", cell.strip().replace("%", ""))


def as_time(cell):
    """0:47 / 00:00:47 / 1:02:03 -> seconds, else None."""
    m = TIME.match(bare(cell))
    if not m:
        return None
    a, b, c = m.groups()
    if c is None:
        return int(a) * 60 + int(b)
    return int(a) * 3600 + int(b) * 60 + float(c.replace(",", "."))


def _thousands_shaped(cell, sep):
    """1,234 / 12,345,678: a first group of 1-3 digits not starting with 0, then groups of 3."""
    return re.fullmatch(r"-?[1-9]\d{0,2}(?:%s\d{3})+" % re.escape(sep), cell) is not None


def decimal_mark(cells, prefer):
    """Which of ',' and '.' is the decimal mark in a column. Any unambiguous cell decides:
    '1.234,5' (both marks: the last is decimal), '1,234,567' (a mark twice: thousands), '80,5' or
    '0,820' (not shaped like thousands: decimal). Only a column where every such cell looks like
    '1,234' is ambiguous, and then the file's locale (`prefer`) decides."""
    cells = [bare(c) for c in cells if as_time(c) is None]
    for c in cells:
        if "," in c and "." in c:
            return "," if c.rfind(",") > c.rfind(".") else "."
    for sep, other in ((",", "."), (".", ",")):
        with_sep = [c for c in cells if sep in c]
        if any(c.count(sep) > 1 for c in with_sep):
            return other
        if any(not _thousands_shaped(c, sep) for c in with_sep):
            return sep
    return prefer


def number(cell, mark):
    c = bare(cell)
    t = as_time(c)
    if t is not None:
        return t
    thousands = "." if mark == "," else ","
    c = c.replace(thousands, "").replace(mark, ".")
    try:
        return float(c)
    except ValueError:
        return None


# --- finding the table ----------------------------------------------------------------------------
def sniff(text):
    """The column separator that gives an even table: ; and tab first, since , may be a decimal mark."""
    lines = [l for l in text.splitlines() if l.strip()][:30]
    for d in (";", "\t", ","):
        widths = {len(r) for r in csv.reader(lines, delimiter=d)}
        if len(widths) == 1 and widths.pop() >= 2:
            return d
    return ","


def table(text):
    d = sniff(text)
    return d, [r for r in csv.reader(io.StringIO(text, newline=""), delimiter=d) if any(c.strip() for c in r)]


def has(header, key):
    h = lang.normalize(header)
    return any(w in h for w in CFG["headers"][key])


def numeric(cell):
    return number(cell, ".") is not None or as_time(cell) is not None


def understand(text, code_choice):
    """-> dict with xs, ys (percent still watching), axis ('percent' or 'seconds'), language."""
    delim, rows = table(text)
    first = next((i for i, r in enumerate(rows) if sum(numeric(c) for c in r) >= 2), None)
    if first is None:
        return None
    header = rows[first - 1] if first else []
    data = [r for r in rows[first:] if sum(numeric(c) for c in r) >= 2]
    code = lang.resolve(code_choice, " ".join(header) or text[:400])
    # columns: by header when the header names them, else the first two numeric columns
    width = max(len(r) for r in data)
    cols = [i for i in range(width) if sum(numeric(r[i]) for r in data if i < len(r)) >= len(data) * 0.8]
    ix = next((i for i in cols if i < len(header) and has(header[i], "position")), None)
    ret = [i for i in cols if i < len(header) and i != ix and has(header[i], "retention")]
    iy = next((i for i in ret if not has(header[i], "relative")), ret[0] if ret else None)
    if ix is None or iy is None:
        if len(cols) < 2:
            return None
        ix, iy = cols[0], cols[1]
    # Only a column of 1,234-shaped cells needs this: the header's language decides, and the
    # separator only when there is no header (a ; file is almost always a decimal-comma locale).
    prefer = "," if (code == "ru" or (not header and delim == ";")) else "."
    xcells = [r[ix] for r in data if ix < len(r)]
    ycells = [r[iy] for r in data if iy < len(r)]
    xm, ym = decimal_mark(xcells, prefer), decimal_mark(ycells, prefer)
    pts = [(number(r[ix], xm), number(r[iy], ym)) for r in data if max(ix, iy) < len(r)]
    pts = [(x, y) for x, y in pts if x is not None and y is not None]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    hx = header[ix] if ix < len(header) else ""
    if any(as_time(c) is not None for c in xcells) or (has(hx, "seconds") and not has(hx, "percent")):
        axis = "seconds"
    elif has(hx, "percent"):
        axis = "percent"
    else:
        axis = "percent" if xs and max(xs) <= 100.5 else "seconds"  # the original rule, as a fallback
    if axis == "percent" and xs and max(xs) <= 1.0:
        xs = [x * 100 for x in xs]  # position as a 0..1 ratio
    if ys and ys[0] <= 1.5 and max(ys) <= 3:
        ys = [y * 100 for y in ys]  # still-watching as a ratio, not a percentage
    return {"xs": xs, "ys": ys, "axis": axis, "lang": code}


def load(path, code_choice):
    """Read a CSV, or the CSV inside a Studio zip. Returns (data, the name of what was read)."""
    if not os.path.exists(path):
        raise Problem("missing", path=path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            found = []
            for n in names:
                if n.lower().endswith((".csv", ".tsv", ".txt")):
                    got = understand(lang.decode(z.read(n), n), code_choice)
                    if got and len(got["xs"]) >= CFG["min_points"]:
                        found.append((len(got["xs"]), n, got))
        if not found:
            raise Problem("zip_none", path=os.path.basename(path), files=", ".join(names) or "-")
        _, name, got = max(found, key=lambda f: f[0])  # the chart has many points, totals have one
        return got, f"{path} -> {name}"
    got = understand(lang.read_text(path), code_choice)
    return got or {"xs": [], "ys": [], "axis": "percent", "lang": lang.resolve(code_choice, "")}, path


# --- the report -----------------------------------------------------------------------------------
def fmt(x, nd, code):
    s = f"{x:.{nd}f}"
    return s.replace(".", ",") if code == "ru" else s


def analyse(d, dur, cues):
    xs, ys, pct = d["xs"], d["ys"], d["axis"] == "percent"
    rows = list(zip(xs, ys))

    def at(x):
        return (x / 100.0 * dur) if (pct and dur) else (x if not pct else None)
    start = ys[0] or 100.0
    # HOOK: the first 30 seconds, or the first 10% when the axis is a percentage and we have no duration
    cutoff = CFG["hook_seconds"] if not pct else (
        CFG["hook_seconds"] / dur * 100 if dur else CFG["hook_percent_without_duration"])
    hook_end = min((y for x, y in rows if x <= cutoff), default=start)
    hook_leak = start - hook_end
    drops = []
    for i in range(1, len(rows)):
        d_ = ys[i - 1] - ys[i]
        span = xs[i] - xs[i - 1] or 1
        drops.append((d_ / span, xs[i - 1], xs[i], d_))
    drops.sort(reverse=True)
    # A drop that ends inside the hook is already the hook leak; listing it again as a cliff
    # pushed the real moments off the list.
    later = [r for r in drops if r[2] > cutoff]
    cliffs = []
    for _, a1, b1, d_ in later[:CFG["cliffs_shown"]]:
        if d_ > CFG["cliff_min_drop"]:
            s0, s1 = at(a1), at(b1)
            cliffs.append({"from": round(a1, 2), "to": round(b1, 2), "lost": round(d_, 2),
                           "at_seconds": None if s0 is None else round(s0, 1),
                           "to_seconds": None if s1 is None else round(s1, 1)})
    mid = [r[0] for r in drops if r[1] > cutoff]
    slide = sum(mid) / len(mid) if mid else 0
    said = {}
    if cues:
        pad = CFG["said_window_pad_seconds"]
        for c in cliffs:
            if c["at_seconds"] is None:
                continue
            # people left somewhere between the two points: say everything spoken across the drop
            near = [q[2] for q in cues if q[0] <= c["to_seconds"] + pad and q[1] >= c["at_seconds"] - pad]
            said[str(c["from"])] = " ".join(near)[:CFG["said_max_chars"]]
    return {"points": len(rows), "start": start, "hook_leak": round(hook_leak, 2), "end": ys[-1],
            "cliffs": cliffs, "slide_per_unit": round(slide, 3), "said": said}


def where(c, code, axis):
    if c["at_seconds"] is not None:
        a, b = c["at_seconds"], c["to_seconds"]
        return f"{a:.0f}-{b:.0f}s" if code == "en" else f"{a:.0f}–{b:.0f} с"
    return f"{fmt(c['from'], 0, code)}-{fmt(c['to'], 0, code)}%"


def report_en(src, d, out, notes):
    cliffs, said = out["cliffs"], out["said"]
    print(f"\n  {src}   {out['points']} points   {d['ys'][0]:.1f}% -> {d['ys'][-1]:.1f}%\n")
    for n in notes:
        print(f"  {n}")
    if notes:
        print()
    leak = out["hook_leak"]
    verdict = "healthy" if leak < CFG["hook_healthy_below"] else "leaking" if leak < CFG["hook_severe_from"] else "severe"
    print(f"  HOOK LEAK   {leak:.1f}% lost in the opening   [{verdict}]")
    print(f"              under 25 is healthy for this length. Fix the first line before anything else.\n")
    print("  CLIFFS      the moments people actually left")
    for c in cliffs:
        print(f"    -{c['lost']:5.1f}%  at {where(c, 'en', d['axis']):>9}"
              + (f"   \"{said.get(str(c['from']), '')}\"" if said else ""))
    if not cliffs:
        print("    none steeper than 0.8% - the loss is all slide, not moments")
    print(f"\n  SLIDE       {out['slide_per_unit']:.3f}% per unit across the middle")
    print("              a flat slide is pacing, not content. Cut the middle, do not rewrite it.\n")


def report_ru(src, d, out, notes):
    cliffs, said = out["cliffs"], out["said"]
    print(f"\n  {src}   точек: {out['points']}   {fmt(d['ys'][0], 1, 'ru')}% -> {fmt(d['ys'][-1], 1, 'ru')}%\n")
    for n in notes:
        print(f"  {n}")
    if notes:
        print()
    leak = out["hook_leak"]
    verdict = ("норма" if leak < CFG["hook_healthy_below"] else
               "утечка" if leak < CFG["hook_severe_from"] else "сильная утечка")
    print(f"  ХУК         в начале ушли {fmt(leak, 1, 'ru')}% зрителей   [{verdict}]")
    print("              Норма — меньше 25%. Сначала исправьте первую фразу, потом всё остальное.\n")
    print("  ОБРЫВЫ      моменты, в которые зрители уходили")
    for c in cliffs:
        print(f"    -{fmt(c['lost'], 1, 'ru'):>5}%  на {where(c, 'ru', d['axis']):>10}"
              + (f"   «{said.get(str(c['from']), '')}»" if said else ""))
    if not cliffs:
        print("    обрывов круче 0,8% нет: зрители уходят постепенно, а не в конкретный момент")
    unit = "за 1% длины ролика" if d["axis"] == "percent" else "в секунду"
    print(f"\n  СПАД        {fmt(out['slide_per_unit'], 3, 'ru')}% {unit} в середине ролика")
    print("              Ровный спад — это темп, а не содержание. Сократите середину, не переписывайте её.\n")


def main():
    lang.setup_output()
    a = sys.argv[1:]
    try:
        choice, a = lang.take_lang_flag(a)
    except SystemExit as e:
        print(e); sys.exit(2)
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    tr = a[a.index("--transcript") + 1] if "--transcript" in a and a.index("--transcript") + 1 < len(a) else None
    dur_arg = a[a.index("--duration") + 1] if "--duration" in a and a.index("--duration") + 1 < len(a) else None
    files = [x for x in a if not x.startswith("--") and x not in (tr, dur_arg)]
    if not files:
        print(__doc__); sys.exit(1)
    code = choice if choice in lang.LANGS else "en"
    try:
        d, src = load(files[0], choice)
        code = d["lang"]
        if len(d["xs"]) < CFG["min_points"]:
            raise Problem("few_points", n=CFG["min_points"])
        dur = None
        if dur_arg is not None or "--duration" in a:
            try:
                dur = float(str(dur_arg).replace(",", "."))
            except ValueError:
                raise Problem("bad_duration")
        cues, notes = None, []
        if tr:
            if not os.path.exists(tr):
                raise Problem("no_transcript", path=tr)
            from transcript import load as load_cues
            cues = load_cues(tr)
            if d["axis"] == "percent" and dur is None and cues:
                dur = cues[-1][1]
                notes.append(f"video length taken from the end of the transcript: {dur:.0f}s" if code == "en" else
                             f"Длина ролика взята из конца транскрипта: {dur:.0f} с")
        if d["axis"] == "percent" and dur is None:
            notes.append("positions are % of the video - add --duration SECONDS or --transcript to get seconds"
                         if code == "en" else
                         "Позиции даны в % длины ролика. Чтобы получить секунды, добавьте --duration "
                         "(длина ролика в секундах) или --transcript")
    except Problem as p:
        print(p.text(code)); sys.exit(1)
    out = analyse(d, dur, cues)
    if as_json:
        out.update({"source": src, "axis": d["axis"], "duration": dur, "lang": code})
        print(json.dumps(out, indent=1, ensure_ascii=False)); return
    (report_ru if code == "ru" else report_en)(src, d, out, notes)


if __name__ == "__main__":
    main()
