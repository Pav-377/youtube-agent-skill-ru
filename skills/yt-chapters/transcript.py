#!/usr/bin/env python3
# Source of truth: shared/transcript.py. tools/build.py copies it into every skill that reads
# transcripts (yt-edit, yt-retention, yt-chapters). Edit this file, never a copy.
"""transcript.py - read a timestamped transcript: .srt, .vtt (including YouTube's automatic
captions) or whisper .json.

    from transcript import load, load_words
    cues = load("transcript.srt")              # [(start_seconds, end_seconds, text), ...]
    words, exact = load_words("auto.ru.vtt")   # [Word(start, end, text), ...], True if timed per word

One parser for deadair.py, chapters.py and retention.py. It used to live inside deadair.py, which
meant the other two skills only worked when yt-edit sat next to them on disk.

YouTube's automatic captions (.vtt from the video page or yt-dlp) are not plain subtitles. Each
line is shown twice - once while it is being spoken, with a <00:00:01.234> time before every word,
and again as the top line of the next cue - and between them sit 10 ms cues that repeat both lines.
Read naively that is every sentence two or three times, with the timing tags in the text. Here the
timed line is the only one taken, so each sentence appears once, and the tags give every word its
own start time. That is the most exact source of word timing there is.

Word timing by source, best first:
  1. YouTube automatic captions (.vtt)   exact start of every word
  2. whisper .json with word timestamps   exact (whisper --word_timestamps True)
  3. .srt / plain .vtt / whisper without words   estimated: a cue's time is shared out by the
     number of characters before each word, so a long word takes longer than a short one
"""
import html, json, re
from collections import namedtuple

import lang

Word = namedtuple("Word", "start end text")

TIMING = re.compile(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)")
INLINE_TS = re.compile(r"<(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})>")
TAG = re.compile(r"<[^>]*>")
LAST_WORD_SECONDS_PER_LETTER = 0.08


def parse_ts(s):
    s = s.strip().replace(",", ".")
    p = s.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[0]) * 60 + float(p[1])


def clean(text):
    """Caption markup out (<i>, <c.colorE5E5E5>, <v Speaker>), entities decoded, spaces collapsed."""
    return re.sub(r"\s+", " ", html.unescape(TAG.sub("", text))).strip()


def _blocks(raw):
    """[(start, end, [raw lines])]. A cue's text runs until an empty line; numbering lines and the
    header (WEBVTT, Kind:, Language:, NOTE ...) never get into the text."""
    cues, cur = [], None
    for line in raw.splitlines():
        m = TIMING.match(line)
        if m:
            cur = [parse_ts(m.group(1)), parse_ts(m.group(2)), []]
            cues.append(cur)
        elif not line.strip():
            # An empty line ends a cue - but only once the cue has text: YouTube's automatic
            # captions put a blank (" ", or "" once an editor trims it) right after the timing.
            if cur is not None and any(l.strip() for l in cur[2]):
                cur = None
        elif cur is not None and not line.strip().isdigit():
            cur[2].append(line)
    return cues


def _youtube_auto(blocks):
    """-> [(start, end, text, [Word])] for YouTube automatic captions, one entry per spoken line."""
    lines, recent = [], []
    for a, b, raw_lines in blocks:
        for raw in raw_lines:
            if INLINE_TS.search(raw):
                parts = INLINE_TS.split(raw)  # text, time, text, time, text ...
                timed = [(a, parts[0])] + [(parse_ts(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]
                words = [[t, w] for t, piece in timed for w in clean(piece).split()]
            else:
                text = clean(raw)
                if not text or lang.normalize(text) in recent:
                    continue  # a repeat of a line already taken
                words = [[a, w] for w in text.split()]  # e.g. [Музыка]: a cue with no word times
            if not words:
                continue
            text = " ".join(w for _, w in words)
            lines.append([words[0][0], b, text, words])
            recent = (recent + [lang.normalize(text)])[-3:]
    out = []
    for i, (start, end, text, words) in enumerate(lines):
        nxt = lines[i + 1][0] if i + 1 < len(lines) else end
        stop = min(end, nxt) if nxt > start else end
        ws = []
        for j, (t, w) in enumerate(words):
            if j + 1 < len(words):
                t_end = words[j + 1][0]
            else:
                # YouTube gives no end for a line's last word, and the cue runs on until the next
                # line - stretching the word to it would hide the pause after it. A spoken word
                # takes about 0.08 s a letter, so it ends there unless the next line starts first.
                t_end = min(max(stop, t), t + max(0.3, LAST_WORD_SECONDS_PER_LETTER * len(w)))
            ws.append(Word(round(t, 3), round(t_end, 3), w))
        out.append((start, max(stop, ws[-1].end), text, ws))
    return out


def _estimate(start, end, text):
    """Share a cue's time out by characters before each word (the owner's rule for .srt)."""
    toks = text.split()
    if not toks:
        return []
    total = max(1, len(text))
    span = max(0.0, end - start)
    out, pos = [], 0
    for i, tok in enumerate(toks):
        at = text.index(tok, pos)
        pos = at + len(tok)
        s = start + span * at / total
        out.append([s, tok])
    return [Word(round(s, 3), round(out[i + 1][0] if i + 1 < len(out) else end, 3), w)
            for i, (s, w) in enumerate(out)]


def _parse(path):
    """-> (cues as [(start, end, text, [Word])], words_are_exact)."""
    raw = lang.read_text(path)
    if path.lower().endswith(".json"):
        d = json.loads(raw)
        segs = d.get("segments", d if isinstance(d, list) else [])
        cues, exact = [], bool(segs) and all(s.get("words") for s in segs)
        for s in segs:
            a, b, text = float(s["start"]), float(s["end"]), (s.get("text") or "").strip()
            if s.get("words"):
                ws = [Word(round(float(w["start"]), 3), round(float(w["end"]), 3),
                           (w.get("word") or w.get("text") or "").strip()) for w in s["words"]]
                ws = [w for w in ws if w.text]
            else:
                ws = _estimate(a, b, text)
            cues.append((a, b, text, ws))
        return cues, exact
    blocks = _blocks(raw)
    if any(INLINE_TS.search(line) for _, _, lines in blocks for line in lines):
        return _youtube_auto(blocks), True
    cues = []
    for a, b, lines in blocks:
        text = clean(" ".join(l.strip() for l in lines))
        if text:
            cues.append((a, b, text, _estimate(a, b, text)))
    return cues, False


def load(path):
    """[(start_seconds, end_seconds, text)] - one entry per caption line."""
    return [(a, b, t) for a, b, t, _ in _parse(path)[0]]


def load_words(path):
    """([Word(start, end, text)], exact). exact is False when times were shared out by characters."""
    cues, exact = _parse(path)
    return [w for _, _, _, ws in cues for w in ws], exact
