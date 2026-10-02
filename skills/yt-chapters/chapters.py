#!/usr/bin/env python3
"""chapters.py - YouTube chapters from a timestamped transcript.

    python3 chapters.py transcript.srt            # or .vtt / whisper .json
    python3 chapters.py transcript.srt --target 8 --json

Prints a description block you can paste straight under a video. YouTube's own rules, enforced here
rather than assumed: the list must start at 00:00, needs at least three entries, and each chapter
must be at least 10 seconds long. A block that breaks any of those silently does not become
chapters, which is why this checks instead of trusting.

Boundaries come from the gaps - the pauses you actually took between sections - scored by how long
the pause was and how much the vocabulary changes across it. It is a first draft you retitle, not a
summariser.
"""
import json, os, re, sys

import lang
from transcript import load  # same parser as yt-edit, copied into this folder by tools/build.py

STOP = set("the a an of for to in on and or is are was were be been with this that it as at by from "
           "you your i my we our they them he she but so if then than there here what which who how "
           "when where why not no yes do does did just really very like about into over out up down "
           "can could will would should have has had get got make made go going went one two".split())

STOP_RU = {lang.normalize(w) for w in lang.read_json(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "chapters.json"))["stop_ru"]}
STOP_STEMS = {lang.stem(w) for w in STOP_RU}

def topical(w):
    """A Russian word that can name a topic: 4+ letters, not a stop word, not an indefinite
    (как-то, какие-то, кто-нибудь) and not a form of a stop word (моей, мной -> мой, я)."""
    if len(w) < 4 or w in STOP_RU or re.search(r"-(?:то|либо|нибудь|таки)$", w):
        return False
    return lang.stem(w) not in STOP_STEMS

def keywords(text, code="en"):
    """Topic words. Russian ones are compared by stem, so "монтаж" and "монтажа" are one word."""
    if code == "ru":
        return {lang.stem(w) for w in lang.words(text) if topical(w)}
    return {w for w in re.findall(r"[a-z']{4,}", text.lower()) if w not in STOP}

def title_ru(text):
    """The three most frequent topic words of a section, each in the form it was first said."""
    counts, first, order = {}, {}, []
    for w in lang.words(text):
        if not topical(w):
            continue
        s = lang.stem(w)
        if s not in counts:
            first[s], counts[s] = w, 0
            order.append(s)
        counts[s] += 1
    top = sorted(order, key=lambda s: (-counts[s], order.index(s)))[:3]
    return " ".join(first[s] for s in top).capitalize() or "Раздел"

def mmss(t):
    t = int(t); h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def main():
    lang.setup_output()
    a = sys.argv[1:]
    choice, a = lang.take_lang_flag(a)
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    target = int(a[a.index("--target") + 1]) if "--target" in a else 7
    a = [x for x in a if not x.startswith("--") and not x.isdigit()]
    if not a or not os.path.exists(a[0]): print(__doc__); sys.exit(1)
    cues = load(a[0])
    if len(cues) < 6: print("too few cues to chapter"); sys.exit(1)
    dur = cues[-1][1]
    code = lang.resolve(choice, " ".join(c[2] for c in cues[:200]))
    cand = []
    # Compare the vocabulary over windows that grow with the video: 12 lines is about 40 seconds,
    # fine for a 5-minute video, noise for an hour-long conversation.
    win = max(12, len(cues) // (target * 4))
    for i in range(1, len(cues)):
        gap = cues[i][0] - cues[i - 1][1]
        before = " ".join(c[2] for c in cues[max(0, i - win):i])
        after = " ".join(c[2] for c in cues[i:i + win])
        kb, ka = keywords(before, code), keywords(after, code)
        shift = 1 - (len(kb & ka) / len(kb | ka)) if (kb | ka) else 0
        cand.append((gap * 1.6 + shift * 3.2, cues[i][0], i))
    cand.sort(reverse=True)
    picked, MIN = [0.0], 10.0
    # Boundaries at least a third of an even split apart. With only YouTube's 10 s minimum, a long
    # video put all its chapters into one busy stretch (an 85-minute podcast got six of seven in its
    # last four minutes). Up to 3.5 minutes with 7 chapters this is the 10 s it always was.
    spacing = max(MIN, dur / (target * 3))
    for _, t, i in cand:
        if len(picked) >= target: break
        if all(abs(t - p) >= spacing for p in picked) and dur - t >= spacing:
            picked.append(t)
    picked.sort()
    chapters = []
    for n, t in enumerate(picked):
        end = picked[n + 1] if n + 1 < len(picked) else dur
        text = " ".join(c[2] for c in cues if c[0] >= t and c[1] <= end)
        if code == "ru":
            chapters.append({"start": round(t, 2), "label": mmss(t), "draft_title": title_ru(text),
                             "seconds": round(end - t, 2)})
            continue
        low = text.lower()
        # Most frequent first; ties go to the word said first. Without the tie-break the order came
        # from set iteration and changed from one run to the next.
        kw = sorted(keywords(text), key=lambda w: (-low.count(w), low.find(w)))
        title = " ".join(w.capitalize() for w in kw[:3]) or "Section"
        chapters.append({"start": round(t, 2), "label": mmss(t), "draft_title": title,
                         "seconds": round(end - t, 2)})
    ok = len(chapters) >= 3 and chapters[0]["start"] == 0 and all(c["seconds"] >= MIN for c in chapters)
    if as_json:
        print(json.dumps({"valid": ok, "chapters": chapters}, indent=1, ensure_ascii=False)); return
    print()
    for c in chapters: print(f"  {c['label']} {c['draft_title']}")
    if code == "ru":
        print(f"\n  глав: {len(chapters)}"
              f"{'' if ok else '  -- НЕ ПОДОЙДЁТ: YouTube нужны минимум 3 главы, первая с 0:00, каждая от 10 секунд'}")
        print("  Переименуйте каждую строку перед вставкой: это слова темы, а не ваши слова.\n")
        return
    print(f"\n  {len(chapters)} chapters"
          f"{'' if ok else '  -- INVALID: YouTube needs 3+, a 00:00 first entry and 10s minimum each'}")
    print("  Retitle every line before pasting. These are the topic words, not your words.\n")

if __name__ == "__main__":
    main()
