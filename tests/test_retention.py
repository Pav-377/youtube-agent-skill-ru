"""retention.py on every export shape we know of (brief 5.5).

One retention curve is written in every combination that makes sense - column separator, decimal
mark, thousands separator, % sign, 0..1 ratios, time format, header language, file encoding - and
each file has to give exactly the analysis the plain canonical file gives.
"""
import csv, io, itertools, json, os, tempfile, unittest, zipfile

from helpers import fixture, run_json, run_script

SCRIPT = "yt-retention/retention.py"
HEADERS = {"en": ("Video position (seconds)", "Video position (%)", "Absolute audience retention (%)"),
           "ru": ("Позиция в видео (сек.)", "Позиция в видео (%)", "Абсолютное удержание аудитории (%)")}
NBSP, NNBSP = " ", " "


def curve(axis):
    """1500 s video: hook drop to 30 s, cliffs at 420-450 s and 990-1020 s, slow slide otherwise."""
    pts, y = [], 100.0
    for i in range(51):
        t = i * 30
        if 0 < t <= 30:
            y -= 18.0
        elif t > 30:
            y -= 0.4 + (4.5 if t == 450 else 0) + (3.5 if t == 1020 else 0)
        pts.append((t if axis == "seconds" else round(t / 1500 * 100, 4), round(y, 1)))
    return pts


def fmt_num(v, decimals, mark, thousands):
    s = f"{v:,.{decimals}f}".replace(",", "\0")
    s = s.replace(".", mark).replace("\0", thousands)
    return s


def fmt_time(t, style):
    t = int(t)
    if style == "m:ss":
        return f"{t // 60}:{t % 60:02d}"
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def write(path, rows, encoding):
    if encoding == "utf-8-sig":
        data = "﻿".encode("utf-8") + rows.encode("utf-8")
    else:
        data = rows.encode(encoding)
    with open(path, "wb") as fh:
        fh.write(data)


def build(axis, header_lang, delim, mark, thousands, pct_sign, ratio, time_style):
    hx = HEADERS[header_lang][0 if axis == "seconds" else 1]
    out = io.StringIO()
    w = csv.writer(out, delimiter=delim, lineterminator="\n")
    w.writerow([hx, HEADERS[header_lang][2]])
    for x, y in curve(axis):
        if axis == "seconds" and time_style:
            xs = fmt_time(x, time_style)
        elif axis == "seconds":
            xs = fmt_num(x, 0, mark, thousands)
        else:
            xs = fmt_num(x / 100 if ratio else x, 6 if ratio else 4, mark, "")
        yv = y / 100 if ratio else y
        ys = fmt_num(yv, 3 if ratio else 1, mark, "") + ("%" if pct_sign and not ratio else "")
        w.writerow([xs, ys])
    return out.getvalue()


def combos():
    """Every combination a real export could plausibly have. English files use a decimal point
    and comma thousands; Russian files a decimal comma or point and space thousands."""
    for axis, hl, delim, pct_sign, ratio in itertools.product(
            ("seconds", "percent"), ("en", "ru"), (",", ";", "\t"), (True, False), (False, True)):
        marks = (".",) if hl == "en" else (",", ".")
        thousands = (("", ",") if hl == "en" else ("", " ", NBSP, NNBSP)) if axis == "seconds" else ("",)
        times = (None, "m:ss", "hh:mm:ss") if axis == "seconds" else (None,)
        encs = ("utf-8", "utf-8-sig", "utf-16") + (("cp1251",) if hl == "ru" else ())
        for mark, th, ts, enc in itertools.product(marks, thousands, times, encs):
            if th and ts:
                continue  # a time cell has no thousands
            if th == mark:
                continue
            if enc == "cp1251" and th == NNBSP:
                continue  # cp1251 has no narrow no-break space, so such a file cannot exist
            yield axis, hl, delim, mark, th, pct_sign, ratio, ts, enc


KEYS = ("points", "hook_leak", "cliffs", "slide_per_unit", "axis")


def analysis(r):
    return {k: r[k] for k in KEYS}


def in_process(path):
    """Read and analyse a file with the module itself: the same code path as the command line,
    without starting several hundred Python processes."""
    d, _ = retention.load(path, "auto")
    out = retention.analyse(d, 1500.0, None)
    out.update({"axis": d["axis"], "lang": d["lang"]})
    return out


import sys  # noqa: E402
from helpers import SKILLS  # noqa: E402
sys.path.insert(0, os.path.join(SKILLS, "yt-retention"))
import retention  # noqa: E402
sys.path.pop(0)


class EveryFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.canon = {}
        for axis in ("seconds", "percent"):
            path = os.path.join(cls.tmp, f"canon_{axis}.csv")
            write(path, build(axis, "en", ",", ".", "", False, False, None), "utf-8")
            cls.canon[axis] = analysis(run_json(SCRIPT, path, "--duration", "1500"))
            # the in-process path must agree with the command line, or the big test proves nothing
            assert analysis(in_process(path)) == cls.canon[axis]

    def test_canonical_files_read_as_designed(self):
        s = self.canon["seconds"]
        self.assertEqual(s["points"], 51)
        self.assertAlmostEqual(s["hook_leak"], 18.0)
        self.assertEqual([(c["at_seconds"], c["to_seconds"]) for c in s["cliffs"][:2]], [(420, 450), (990, 1020)])
        secs = lambda r: [(c["at_seconds"], c["to_seconds"]) for c in r["cliffs"][:2]]
        self.assertEqual(secs(self.canon["percent"]), secs(s))

    def test_all_combinations_agree(self):
        n = 0
        for i, (axis, hl, delim, mark, th, pct, ratio, ts, enc) in enumerate(combos()):
            label = f"{axis} {hl} delim={delim!r} mark={mark!r} th={th!r} %={pct} ratio={ratio} time={ts} {enc}"
            with self.subTest(label):
                path = os.path.join(self.tmp, f"f{i}.csv")
                write(path, build(axis, hl, delim, mark, th, pct, ratio, ts), enc)
                r = in_process(path)
                self.assertEqual(analysis(r), self.canon[axis])
                self.assertEqual(r["lang"], hl)
            n += 1
        self.assertGreater(n, 200)


class Locale(unittest.TestCase):
    def test_p2_demo_reads_19_5(self):
        """The video's demo: decimal comma, Russian report."""
        p = run_script(SCRIPT, fixture("ru", "retention_ru_comma.csv"))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("в начале ушли 19,5% зрителей", p.stdout)

    def test_english_thousands_vs_russian_decimal(self):
        """'1,234' is 1234 in an English file and 1.234 in a Russian one."""
        with tempfile.TemporaryDirectory() as tmp:
            en, ru = os.path.join(tmp, "en.csv"), os.path.join(tmp, "ru.csv")
            rows = [(i * 100 + 34, 100 - i) for i in range(12)]
            with open(en, "w", encoding="utf-8") as fh:
                fh.write("Video position (seconds),Audience retention (%)\n")
                fh.writelines(f'"{x // 1000},{x % 1000:03d}",{y}\n' if x >= 1000 else f"{x},{y}\n" for x, y in rows)
            with open(ru, "w", encoding="utf-8") as fh:
                fh.write("Позиция в видео (%);Удержание аудитории (%)\n")
                fh.writelines(f"{i},{234 + i:03d};{100 - i},5\n" for i in range(12))
            r_en = run_json(SCRIPT, en)
            r_ru = run_json(SCRIPT, ru)
        self.assertEqual(r_en["axis"], "seconds")
        self.assertEqual(r_ru["axis"], "percent")
        self.assertEqual(r_ru["start"], 100.5)

    def test_header_picks_absolute_over_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Video position (%),Relative audience retention,Absolute audience retention (%)\n")
                fh.writelines(f"{i * 10},0.5,{100 - i * 3}\n" for i in range(11))
            r = run_json(SCRIPT, path)
        self.assertEqual(r["start"], 100)
        self.assertEqual(r["end"], 70)


class Archives(unittest.TestCase):
    def zip_with(self, tmp, files):
        path = os.path.join(tmp, "export.zip")
        with zipfile.ZipFile(path, "w") as z:
            for name, text in files.items():
                z.writestr(name, text.encode("utf-8"))
        return path

    def test_finds_the_chart_among_other_tables(self):
        chart = build("percent", "ru", ",", ",", "", True, False, None)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.zip_with(tmp, {"Totals.csv": "Показатель,Значение\nПросмотры,1000\n",
                                       "Table data.csv": "Видео,Удержание (%)\nРолик,45,3\n",
                                       "Chart data.csv": chart})
            r = run_json(SCRIPT, path, "--duration", "1500")
        self.assertEqual(r["points"], 51)
        self.assertTrue(r["source"].endswith("Chart data.csv"))

    def test_archive_without_a_chart_names_its_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.zip_with(tmp, {"Totals.csv": "Показатель,Значение\nПросмотры,1000\n"})
            p = run_script(SCRIPT, path)
        self.assertEqual(p.returncode, 1)
        self.assertIn("Totals.csv", p.stdout)
        self.assertNotIn("Traceback", p.stderr)


class Messages(unittest.TestCase):
    """Every problem is a sentence with a hint, in the file's language - never a traceback."""

    def run_bad(self, *args):
        p = run_script(SCRIPT, *args)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn("Traceback", p.stderr)
        return p.stdout

    def test_too_few_points_in_russian(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Позиция в видео (%);Удержание (%)\n0;100\n50;60\n")
            self.assertIn("меньше 8 точек", self.run_bad(path))

    def test_missing_file(self):
        self.assertIn("no such file", self.run_bad("nope.csv"))
        self.assertIn("Файл не найден", self.run_bad("nope.csv", "--lang", "ru"))

    def test_missing_transcript(self):
        out = self.run_bad(fixture("ru", "retention_ru_comma.csv"), "--transcript", "nope.srt")
        self.assertIn("Транскрипт не найден", out)

    def test_bad_duration(self):
        self.assertIn("--duration", self.run_bad(fixture("en", "retention_en_pct.csv"), "--duration", "ten"))

    def test_percent_axis_without_length_says_what_to_add(self):
        p = run_script(SCRIPT, fixture("ru", "retention_ru_comma.csv"))
        self.assertIn("--duration", p.stdout)

    def test_decimal_comma_duration(self):
        r = run_json(SCRIPT, fixture("ru", "retention_ru_comma.csv"), "--duration", "600,0")
        self.assertEqual(r["duration"], 600.0)


if __name__ == "__main__":
    unittest.main()
