#!/usr/bin/env python3
# Source of truth: shared/transcript.py. tools/build.py copies it into every skill that reads
# transcripts (yt-edit, yt-retention, yt-chapters). Edit this file, never a copy.
"""transcript.py - read a timestamped transcript: .srt, .vtt or whisper .json.

    from transcript import load
    cues = load("transcript.srt")    # [(start_seconds, end_seconds, text), ...]

One parser for deadair.py, chapters.py and retention.py. It used to live inside deadair.py, which
meant the other two skills only worked when yt-edit sat next to them on disk.
"""
import json, re


def parse_ts(s):
    s = s.strip().replace(",", ".")
    p = s.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[0]) * 60 + float(p[1])


def load(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    if path.endswith(".json"):
        d = json.loads(raw)
        segs = d.get("segments", d if isinstance(d, list) else [])
        return [(float(s["start"]), float(s["end"]), (s.get("text") or "").strip()) for s in segs]
    cues, cur = [], None
    for line in raw.splitlines():
        m = re.match(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", line)
        if m:
            cur = [parse_ts(m.group(1)), parse_ts(m.group(2)), []]
            cues.append(cur)
        elif cur is not None and line.strip() and not line.strip().isdigit():
            cur[2].append(line.strip())
    return [(a, b, " ".join(t)) for a, b, t in cues if t]
