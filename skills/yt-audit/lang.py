#!/usr/bin/env python3
# Source of truth: shared/lang.py (and shared/lang.json). tools/build.py copies both into every
# skill that has a script. Edit these files, never a copy.
"""lang.py - the Russian/English plumbing every script shares. Standard library only.

    import lang
    lang.setup_output()                      # UTF-8 to the console, never a UnicodeEncodeError
    text = lang.read_text(path)              # UTF-8 with or without BOM, UTF-16, cp1251 fallback
    choice, args = lang.take_lang_flag(args) # --lang ru|en|auto, auto by default
    code = lang.resolve(choice, text)        # "ru" or "en"
    lang.tokens("какой-то ролик, 3.5%")      # ['какой-то', 'ролик', '3.5%']
    lang.normalize("Ёлка — «тест»")          # 'елка - "тест"'   (comparison only, never shown)
    lang.stem("монтажа") == lang.stem("монтаж")
    lang.same_word("канал", "каналу")        # True - use this for comparisons, see its docstring

Why each piece exists:
- detect: the scripts have to know which word lists to use. It counts plain words, not letters:
  short Russian titles are full of Latin brand names, and a letter share cannot tell
  "Claude Code + MCP: гайд" from "My trip to Moscow (Москва)". Thresholds are in lang.json.
- tokens: the original scripts found words with [a-z0-9], so Russian text had no words at all.
- normalize: ё/е, non-breaking spaces, typographic dashes and quotes otherwise make two equal words
  compare as different.
- stem: Russian changes the ending of a word for case and number ("монтаж", "монтажа", "монтажу").
  A repeat check that compares whole words misses all of them. This is the Snowball (Porter)
  algorithm for Russian: it removes endings only inside the part of the word after the first
  vowel, so short words survive, which a "first N letters" rule does not manage.
- setup_output / read_text: on a Russian Windows the defaults are cp1251/cp866, so UTF-8 files
  came out as mojibake and an emoji in the output crashed the script.
"""
import codecs, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "lang.json"), encoding="utf-8") as _fh:
    DATA = json.load(_fh)

LANGS = ("ru", "en")

# --- detection -------------------------------------------------------------------------------------


def cyrillic_share(text):
    """Share of letters that are Cyrillic, 0..1. None when the text has no letters at all."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    return sum(1 for c in letters if "Ѐ" <= c <= "ӿ") / len(letters)


def plain_words(text):
    """Words written in lower case, without digits. Capitalised words are left out on purpose:
    brands (Claude, YouTube), models (iPhone, GPT-4) and sentence starts look the same in both
    languages and would drag a short Russian title towards English."""
    return [w for w in tokens(text) if not w[0].isdigit() and w == w.lower()]


def detect(text, default="en"):
    """'ru' or 'en'. Text without letters (numbers, empty) gets `default`. See lang.json."""
    plain = plain_words(text)
    if plain:
        share = sum(1 for w in plain if is_cyrillic(w)) / len(plain)
        return "ru" if share >= DATA["word_share_for_russian"] else "en"
    share = cyrillic_share(text)
    if share is None:
        return default
    return "ru" if share >= DATA["letter_share_for_russian"] else "en"


def take_lang_flag(args):
    """Pull --lang VALUE out of an argument list. Returns (choice, remaining args)."""
    if "--lang" not in args:
        return "auto", list(args)
    i = args.index("--lang")
    value = args[i + 1].lower() if i + 1 < len(args) else ""
    if value not in LANGS + ("auto",):
        raise SystemExit("--lang: ru, en или auto / ru, en or auto")
    return value, list(args[:i]) + list(args[i + 2:])


def resolve(choice, text):
    return choice if choice in LANGS else detect(text)


def plural(n, one, few, many):
    """Russian plural: plural(1, "слово", "слова", "слов") -> "слово"; 3 -> "слова"; 5, 11, 12 -> "слов"."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# --- normalisation and tokens ----------------------------------------------------------------------

_SPACES = dict.fromkeys(map(ord, "       "), " ")
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = dict.fromkeys(map(ord, "«»“”„‟"), '"')
_APOS = dict.fromkeys(map(ord, "‘’‚‛ʼ"), "'")
_TABLE = {**_SPACES, **_DASHES, **_QUOTES, **_APOS, ord("ё"): "е", ord("Ё"): "Е"}


def normalize(text):
    """Lower case, ё -> е, one kind of space, dash and quote. For comparing, never for output."""
    return re.sub(r" {2,}", " ", text.translate(_TABLE)).lower()


# A number (with decimal part and optional %), or a word of letters joined by - or an apostrophe:
# "3.5%", "80,5", "какой-то", "слова-паразиты", "don't". Digits inside a word split it: "GPT-4".
TOKEN = re.compile(r"\d+(?:[.,]\d+)*%?|[^\W\d_]+(?:['’\-][^\W\d_]+)*")


def tokens(text):
    """Words and numbers as they are written - case and ё kept, for showing to the user."""
    return TOKEN.findall(text.translate(_SPACES))


def words(text):
    """Words only (no numbers), normalised for comparison."""
    return [normalize(t) for t in tokens(text) if not t[0].isdigit()]


def is_cyrillic(word):
    return any("Ѐ" <= c <= "ӿ" for c in word)


# --- Russian stemmer (Snowball) --------------------------------------------------------------------

_VOWELS = "аеиоуыэюя"
_GERUND1 = ("в", "вши", "вшись")
_GERUND2 = ("ив", "ивши", "ившись", "ыв", "ывши", "ывшись")
_ADJECTIVE = ("ее", "ие", "ые", "ое", "ими", "ыми", "ей", "ий", "ый", "ой", "ем", "им", "ым", "ом",
              "его", "ого", "ему", "ому", "их", "ых", "ую", "юю", "ая", "яя", "ою", "ею")
_PARTICIPLE1 = ("ем", "нн", "вш", "ющ", "щ")
_PARTICIPLE2 = ("ивш", "ывш", "ующ")
_REFLEXIVE = ("ся", "сь")
_VERB1 = ("ла", "на", "ете", "йте", "ли", "й", "л", "ем", "н", "ло", "но", "ет", "ют", "ны", "ть",
          "ешь", "нно")
_VERB2 = ("ила", "ыла", "ена", "ейте", "уйте", "ите", "или", "ыли", "ей", "уй", "ил", "ыл", "им", "ым",
          "ен", "ило", "ыло", "ено", "ят", "ует", "уют", "ит", "ыт", "ены", "ить", "ыть", "ишь", "ую", "ю")
_NOUN = ("а", "ев", "ов", "ие", "ье", "е", "иями", "ями", "ами", "еи", "ии", "и", "ией", "ей", "ой",
         "ий", "й", "иям", "ям", "ием", "ем", "ам", "ом", "о", "у", "ах", "иях", "ях", "ы", "ь", "ию",
         "ью", "ю", "ия", "ья", "я")
_DERIVATIONAL = ("ост", "ость")


def _regions(w):
    """RV: after the first vowel. R2: R1 of R1, where R1 is after the first vowel-consonant pair."""
    rv = next((i + 1 for i, c in enumerate(w) if c in _VOWELS), len(w))

    def r1_from(start):
        for i in range(start + 1, len(w)):
            if w[i] not in _VOWELS and w[i - 1] in _VOWELS:
                return i + 1
        return len(w)
    r1 = r1_from(0)
    return rv, r1_from(r1)


def _strip(w, limit, after_a=(), plain=()):
    """Remove the longest matching suffix that starts at or after `limit`. Suffixes in `after_a`
    count only when preceded by а or я (inside the limit too), which stays. None if nothing fits."""
    best = None
    for suf in after_a + plain:
        if w.endswith(suf) and len(w) - len(suf) >= limit and (best is None or len(suf) > len(best)):
            best = suf
    if best is None:
        return None
    cut = len(w) - len(best)
    if best in after_a and best not in plain:
        if cut - 1 < limit or w[cut - 1] not in "ая":
            return None
    return w[:cut]


def _stem_ru(w):
    rv, r2 = _regions(w)
    # Step 1: perfective gerund, or (reflexive, then adjectival / verb / noun)
    s = _strip(w, rv, _GERUND1, _GERUND2)
    if s is not None:
        w = s
    else:
        s = _strip(w, rv, plain=_REFLEXIVE)
        if s is not None:
            w = s
        s = _strip(w, rv, plain=_ADJECTIVE)
        if s is not None:
            w = s
            p = _strip(w, rv, _PARTICIPLE1, _PARTICIPLE2)
            if p is not None:
                w = p
        else:
            s = _strip(w, rv, _VERB1, _VERB2)
            if s is None:
                s = _strip(w, rv, plain=_NOUN)
            if s is not None:
                w = s
    # Step 2: a trailing и
    if w.endswith("и") and len(w) - 1 >= rv:
        w = w[:-1]
    # Step 3: derivational ост / ость inside R2
    s = _strip(w, r2, plain=_DERIVATIONAL)
    if s is not None:
        w = s
    # Step 4: superlative ейш(е), then нн -> н, or a soft sign
    s = _strip(w, rv, plain=("ейш", "ейше"))
    if s is not None:
        w = s
    if w.endswith("нн") and len(w) - 2 >= rv:
        w = w[:-1]
    elif w.endswith("ь") and len(w) - 1 >= rv:
        w = w[:-1]
    return w


def stem(word):
    """Stem for comparing words. Russian words go through Snowball; others are only normalised.
    Hyphenated words are stemmed part by part: "слова-паразиты" -> "слов-паразит"."""
    w = normalize(word)
    if not is_cyrillic(w):
        return w
    return "-".join(_stem_ru(part) if is_cyrillic(part) else part for part in w.split("-"))


def _drop_fleeting_vowel(s):
    """ошибок -> ошибк, обложек -> обложк: the vowel that appears only in some forms."""
    if len(s) >= 4 and s[-2] in "ое" and s[-1] not in _VOWELS and s[-3] not in _VOWELS:
        return s[:-2] + s[-1]
    return s


def _same_part(a, b):
    if a == b:
        return True
    if not (is_cyrillic(a) and is_cyrillic(b)):
        return False
    if _drop_fleeting_vowel(a) == _drop_fleeting_vowel(b):
        return True
    short, long_ = sorted((a, b), key=len)
    # Snowball cuts some nouns as if they were verbs: канал -> кана, but каналу -> канал.
    return len(short) >= 4 and long_.startswith(short) and len(long_) - len(short) <= 2


def same_word(a, b):
    """Two words are forms of one word: монтаж/МОНТАЖА, канал/каналу, ошибка/ошибок.

    Use this, not stem(a) == stem(b), wherever a missed match costs the user something (repeats
    between title and thumbnail, topic shifts). Known limit: rare look-alikes such as канал/канат
    count as one word, because 4 shared letters is where the prefix rule starts."""
    sa, sb = stem(a), stem(b)
    pa, pb = sa.split("-"), sb.split("-")
    return len(pa) == len(pb) and all(_same_part(x, y) for x, y in zip(pa, pb))


# --- files and console -----------------------------------------------------------------------------


def setup_output():
    """Make stdout/stderr safe for Cyrillic and emoji.

    A Windows console already gets Unicode from Python. A redirect or a pipe on a Russian Windows
    gets cp1251, which has no emoji and no symbols such as the arrow - one of those and the script
    used to die with UnicodeEncodeError. Such streams are switched to UTF-8. If the user set
    PYTHONIOENCODING themselves, their encoding stays and unknown characters become '?'.
    """
    forced = os.environ.get("PYTHONIOENCODING")
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue  # replaced by something that is not a text stream (some IDEs, older Pythons)
        try:
            if forced:
                stream.reconfigure(errors="replace")
            elif codecs.lookup(stream.encoding or "ascii").name != "utf-8":
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (LookupError, ValueError, OSError):
            pass


def _note(path, text):
    name = os.path.basename(path)
    if detect(text) == "ru":
        msg = (f"Файл {name} сохранён не в UTF-8. Прочитал его как Windows-1251. "
               "Если буквы выглядят странно, пересохраните файл в кодировке UTF-8.")
    else:
        msg = (f"{name} is not UTF-8; read it as Windows-1251. "
               "If the text looks garbled, save the file as UTF-8.")
    print(msg, file=sys.stderr)


def decode(data, name="file"):
    """Bytes to text: UTF-8 with or without BOM, UTF-16 with BOM (Excel's "Unicode text"), and
    cp1251 as a last resort - with a note on stderr saying so. `name` is only for that note."""
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1251", errors="replace")
        _note(name, text)
        return text


def read_text(path):
    """Read a text file whatever Windows saved it as. See decode()."""
    with open(path, "rb") as fh:
        return decode(fh.read(), path)


def read_json(path):
    return json.loads(read_text(path))
