#!/usr/bin/env python3
"""collect.py - gather real Russian YouTube data for calibration. A development tool: it needs
yt-dlp, it talks to YouTube, and it is not part of the plugin.

    python tools/research/collect.py channels "запрос 1" "запрос 2" ...   # find candidate channels
    python tools/research/collect.py videos  CHANNEL_ID ...               # list each channel's videos
    python tools/research/collect.py subs    VIDEO_ID ...                 # Russian automatic captions

Everything goes to _private/research/ and never into the repository: other people's titles and
subtitles are used for measuring, not redistributed. Only subtitles and metadata are downloaded -
never video or audio. Requests are spaced out so as not to hammer YouTube.

Titles are requested in Russian (youtube:lang=ru); without it YouTube may hand back machine
translations into English. View counts are requested in English: in a channel list the Russian page
says "181 тыс. просмотров" and yt-dlp keeps only the 181 (checked: 181 vs 181635), while "181K
views" comes back as 181000 - rounded, but in proportion, which is all a median multiple needs.
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "_private", "research")
PAUSE = 1.5


def ytdlp(*args, timeout=300, lang="ru"):
    p = subprocess.run(["yt-dlp", "--extractor-args", f"youtube:lang={lang}", *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    time.sleep(PAUSE)
    return p


def save(name, data):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def load(name, default):
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def channels(queries):
    """Search results grouped by channel: how often each channel came up, and a sample title."""
    found = load("channels_search.json", {})
    for q in queries:
        p = ytdlp("--flat-playlist", "-J", f"ytsearch40:{q}")
        if p.returncode:
            print(f"  search failed: {q}: {p.stderr.strip()[-200:]}")
            continue
        for e in json.loads(p.stdout).get("entries", []):
            cid = e.get("channel_id")
            if not cid:
                continue
            c = found.setdefault(cid, {"channel": e.get("channel"), "hits": 0, "queries": [], "sample": []})
            c["hits"] += 1
            if q not in c["queries"]:
                c["queries"].append(q)
            if len(c["sample"]) < 3:
                c["sample"].append(e.get("title"))
        print(f"  {q}: {len(found)} channels so far")
    save("channels_search.json", found)


def videos(channel_ids, limit=80):
    """Long videos from each channel's Videos tab (Shorts live on a separate tab): id, title, views."""
    data = load("videos.json", {})
    for cid in channel_ids:
        if cid in data:
            continue
        p = ytdlp("--flat-playlist", "-J", "--playlist-end", str(limit),
                  f"https://www.youtube.com/channel/{cid}/videos")
        if p.returncode:
            print(f"  {cid}: failed: {p.stderr.strip()[-200:]}")
            continue
        d = json.loads(p.stdout)
        q = ytdlp("--flat-playlist", "-J", "--playlist-end", str(limit),
                  f"https://www.youtube.com/channel/{cid}/videos", lang="en")
        views = {e.get("id"): e.get("view_count") for e in json.loads(q.stdout).get("entries", [])} if not q.returncode else {}
        rows = [{"id": e.get("id"), "title": e.get("title"), "views": views.get(e.get("id")),
                 "duration": e.get("duration")} for e in d.get("entries", []) if e.get("id")]
        data[cid] = {"channel": d.get("channel") or d.get("title"), "videos": rows}
        print(f"  {data[cid]['channel']}: {len(rows)} videos")
        save("videos.json", data)


def subs(video_ids):
    """Russian automatic captions as .vtt into _private/research/subs/. Skips what is already there."""
    folder = os.path.join(OUT, "subs")
    os.makedirs(folder, exist_ok=True)
    for vid in video_ids:
        if any(f.startswith(vid + ".") for f in os.listdir(folder)):
            continue
        p = ytdlp("--skip-download", "--write-auto-subs", "--sub-langs", "ru", "--sub-format", "vtt",
                  "-o", os.path.join(folder, "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={vid}")
        ok = any(f.startswith(vid + ".") for f in os.listdir(folder))
        print(f"  {vid}: {'ok' if ok else 'no Russian automatic captions'}"
              + ("" if p.returncode == 0 else f" ({p.stderr.strip()[-120:]})"))


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("channels", "videos", "subs"):
        print(__doc__)
        sys.exit(1)
    {"channels": channels, "videos": videos, "subs": subs}[a[0]](a[1:])


if __name__ == "__main__":
    main()
