#!/usr/bin/env python3
# Source of truth: shared/title.py. tools/build.py copies it into yt-package and yt-audit.
# Edit this file, never a copy.
"""title.py - lint a YouTube title and thumbnail pairing before you publish it.

    python3 title.py --title "..." --thumb "AI RAN IT"
    python3 title.py --title "..." --thumb "БЕЗ МОНТАЖА" --thumb-small "и без программ"
    python3 title.py titles.txt            # one per line, ranked
    python3 title.py --title "..." --json
    python3 title.py --title "..." --lang ru    # ru, en or auto (the default)

The pairing is the unit, not the title. A title that repeats the thumbnail text wastes half the
click surface, and that is the single most common mistake this checks for.

Length: YouTube truncates around 60 characters on desktop search and around 40 on a mobile home
feed. Both limits are reported because they are different failures - a desktop truncation loses the
tail, a mobile one can lose the subject.

Thumbnail text comes in two sizes. --thumb is the big text people read at feed size: only meaningful
words count (not "in", "the", "и", "на"), three is comfortable, four or five gets a hint, six or more
a warning. --thumb-small is the small caption under it, checked on its own. Nothing is blocked:
every finding is advice. Russian titles are checked with Russian word lists, forms of one word
count as one ("монтаж" and "МОНТАЖА" repeat each other), and cheap clickbait gets a warning.
All lists and limits are in title.json.
"""
import json, re, sys, os

import lang

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = lang.read_json(os.path.join(HERE, "title.json"))
DESKTOP, MOBILE, HARD = CFG["desktop"], CFG["mobile"], CFG["hard"]
VAGUE = set(CFG["vague"]["en"])
STOP = set(CFG["stop"]["en"])

LABELS_RU = {"length": "длина", "mobile": "телефон", "shouting": "капс", "vague": "размыто",
             "no-number": "конкретика", "front-load": "начало", "duplicate": "повтор",
             "thumb-length": "обложка", "thumb-small": "подпись", "clickbait": "кликбейт"}


def words(t): return re.findall(r"[a-z0-9']+", t.lower())


# --- Russian helpers -------------------------------------------------------------------------------
def ru_words(t):
    """Words and numbers, normalised (lower case, ё = е)."""
    return [lang.normalize(w) for w in lang.tokens(t)]


def n_ru(n, one, few, many):
    return f"{n} {lang.plural(n, one, few, many)}"


def names(t):
    """Brands and names: a capital letter not at the start of a sentence and not a word in caps."""
    toks = t.split()
    out = []
    for i, tok in enumerate(toks):
        w = re.sub(r"^\W+|\W+$", "", tok)
        starts_sentence = i == 0 or toks[i - 1].endswith((".", "!", "?", "…", ":"))
        if w[:1].isupper() and not (len(w) > 1 and w.isupper()) and not starts_sentence:
            out.append(w)
    return out


def in_list(word, items):
    return any(lang.same_word(word, x) for x in items)


def meaningful(text, code):
    if code == "en":
        return [w for w in words(text) if w not in CFG["thumb_function_words"]["en"]]
    fw = set(CFG["thumb_function_words"]["ru"]) | set(CFG["thumb_function_words"]["en"])
    return [w for w in ru_words(text) if w not in fw]


def shared_words(a, b, stop, code):
    """Words of b that repeat a word of a. Russian compares forms of one word."""
    if code == "en":
        return sorted((set(words(a)) - stop) & (set(words(b)) - stop))
    wa = [w for w in ru_words(a) if w not in stop]
    return sorted({w for w in ru_words(b) if w not in stop and any(lang.same_word(w, x) for x in wa)})


def clickbait(t):
    text = " " + " ".join(ru_words(t)).replace(" %", "%") + " "
    found = []
    for p in CFG["clickbait_ru"]["phrases"]:
        pat = re.escape(lang.normalize(p)).replace(r"\*", r"\w*")
        m = re.search(r"(?<!\w)" + pat + r"(?!\w)", text)
        if m:
            found.append(m.group(0))
    return found


# --- the checks ------------------------------------------------------------------------------------
def check(title, thumb=None, small=None, code="en"):
    t = title.strip()
    n = len(t)
    ru = code == "ru"
    issues, good, hints = [], [], []
    stop = STOP | set(CFG["stop"]["ru"]) if ru else STOP

    def say(en, ru_text):
        return ru_text if ru else en

    if n > HARD: issues.append(("length", say(f"{n} characters - YouTube's hard limit is {HARD}",
                                              f"{n_ru(n, 'символ', 'символа', 'символов')}, а YouTube принимает не больше {HARD}")))
    elif n > DESKTOP: issues.append(("length", say(f"{n} characters - desktop search cuts near {DESKTOP}",
                                                   f"{n_ru(n, 'символ', 'символа', 'символов')}: в поиске на компьютере обрежется около {DESKTOP}")))
    else: good.append(say(f"{n} characters, inside the {DESKTOP}-character desktop cut",
                          f"{n_ru(n, 'символ', 'символа', 'символов')}, помещается в {DESKTOP} символов на компьютере"))
    if n > MOBILE:
        head = t[:MOBILE].rsplit(" ", 1)[0]
        issues.append(("mobile", say(f'a mobile feed shows about "{head}..." - check the subject survives',
                                     f"в ленте на телефоне видно примерно «{head}...». Проверьте, что главное осталось")))
    caps = [w for w in t.split() if len(w) > 2 and w.isupper()]
    if len(caps) > CFG["caps_ceiling"]:
        issues.append(("shouting", say(f"{len(caps)} all-caps words - two is the ceiling before it reads as spam",
                                       f"{n_ru(len(caps), 'слово', 'слова', 'слов')} капсом, а больше двух выглядит как спам")))
    elif caps:
        good.append(say(f"{len(caps)} all-caps word for emphasis", f"{n_ru(len(caps), 'слово', 'слова', 'слов')} капсом для акцента"))
    if ru:
        v = sorted({w for w in ru_words(t) if in_list(w, CFG["vague"]["ru"]) or w in VAGUE})
    else:
        v = sorted({w for w in words(t) if w in VAGUE})
    if v: issues.append(("vague", say(f"{', '.join(v)} - swap for a number, a name or a date",
                                      f"{', '.join(v)}: замените на цифру, имя или дату")))
    nums = re.findall(r"\d[\d,.]*%?", t)
    if ru:
        nums += [w for w in ru_words(t) if in_list(w, CFG["numerals_ru"])] + names(t)
    if nums: good.append(say(f"carries a concrete figure ({', '.join(nums[:3])})",
                             f"есть конкретика ({', '.join(nums[:3])})"))
    else: issues.append(("no-number", say("no number, date or name - the most reliable single fix",
                                          "нет цифры, даты или имени. Это самое надёжное улучшение")))
    if t.endswith("?"): good.append(say("open question in the title", "в заголовке открытый вопрос"))
    first3 = (ru_words(t) if ru else words(t))[:3]
    front = [w for w in first3 if w not in stop]
    if not front: issues.append(("front-load", say("the first three words are all filler - move the subject forward",
                                                   "первые три слова служебные. Перенесите главное в начало")))
    if ru:
        cb = clickbait(t)
        if cb:
            issues.append(("clickbait", "«" + "», «".join(cb) + "»: многие зрители считают такие слова дешёвым "
                                        "кликбейтом. Это предупреждение, решать вам"))
    if thumb:
        shared = shared_words(t, thumb, stop, code)
        if shared:
            issues.append(("duplicate", say(f"thumbnail repeats the title on {', '.join(shared)} - "
                                            "the thumbnail should say what the title does not",
                                            f"обложка повторяет заголовок: {', '.join(shared)}. "
                                            "На обложке нужно то, чего нет в заголовке")))
        else:
            good.append(say("thumbnail and title carry different words", "обложка и заголовок говорят разное"))
        k = len(meaningful(thumb, code))
        if k > CFG["thumb"]["hint_up_to"]:
            issues.append(("thumb-length", say(f"{k} meaningful words on the thumbnail - it will not read at feed size",
                                               f"на обложке {n_ru(k, 'значимое слово', 'значимых слова', 'значимых слов')}: текст не прочитается в ленте")))
        elif k > CFG["thumb"]["ok_up_to"]:
            hints.append(("thumb-length", say(f"{k} meaningful words on the thumbnail - see if it can be shorter",
                                              f"на обложке {n_ru(k, 'значимое слово', 'значимых слова', 'значимых слов')}. Подумайте, можно ли короче")))
    if small:
        k = len(meaningful(small, code))
        if k > CFG["thumb"]["small_max"]:
            issues.append(("thumb-small", say(f"{k} meaningful words in the small caption - over {CFG['thumb']['small_max']} nobody reads",
                                              f"в подписи на обложке {n_ru(k, 'значимое слово', 'значимых слова', 'значимых слов')}, а больше {CFG['thumb']['small_max']} никто не прочитает")))
        rep = shared_words(t, small, stop, code)
        if rep:
            issues.append(("thumb-small", say(f"the small caption repeats the title on {', '.join(rep)}",
                                              f"подпись на обложке повторяет заголовок: {', '.join(rep)}")))
    score = max(0, min(100, 100 - 14 * len(issues) + 4 * len(good)))
    return {"title": t, "chars": n, "score": score, "issues": issues, "good": good, "hints": hints, "lang": code}


def show(r):
    ru = r["lang"] == "ru"
    label = (lambda k: LABELS_RU.get(k, k)) if ru else (lambda k: k)
    print(f'\n  "{r["title"]}"')
    print(f"  {n_ru(r['chars'], 'символ', 'символа', 'символов')}   оценка {r['score']}/100" if ru else f"  {r['chars']} chars   score {r['score']}/100")
    for k, m in r["issues"]: print(f"    x  {label(k):<12} {m}")
    for k, m in r["hints"]:  print(f"    ~  {label(k):<12} {m}")
    for m in r["good"]:      print(f"    {'ок' if ru else 'ok'}              {m}")


def main():
    lang.setup_output()
    a = sys.argv[1:]
    choice, a = lang.take_lang_flag(a)
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    thumb = a[a.index("--thumb") + 1] if "--thumb" in a else None
    small = a[a.index("--thumb-small") + 1] if "--thumb-small" in a else None
    if "--title" in a:
        titles = [a[a.index("--title") + 1]]
    elif a and os.path.exists(a[0]):
        titles = [l for l in lang.read_text(a[0]).splitlines() if l.strip()]
    else:
        print(__doc__); sys.exit(1)
    rows = [check(t, thumb, small, lang.resolve(choice, " ".join([t, thumb or "", small or ""])))
            for t in titles]
    rows.sort(key=lambda r: -r["score"])
    if as_json: print(json.dumps(rows, indent=1, ensure_ascii=False)); return
    for r in rows: show(r)
    print()


if __name__ == "__main__":
    main()
