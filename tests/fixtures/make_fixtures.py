#!/usr/bin/env python3
"""make_fixtures.py - regenerate the synthetic test inputs in tests/fixtures/.

    python tests/fixtures/make_fixtures.py

Every file written here is invented for testing. None of it comes from a real channel, a real
transcript or a real Studio export. Real files from the channel owner live in _private/ and never
reach the repository.

Hand-written fixtures (hooks_en_*.txt, titles_en.txt) are not touched by this script.
The output is deterministic: running it twice gives byte-identical files.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
EN = os.path.join(HERE, "en")
RU = os.path.join(HERE, "ru")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def ts(t, sep=","):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def srt(cues):
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1))


def vtt(cues):
    return "WEBVTT\n\n" + "\n".join(f"{ts(a, '.')} --> {ts(b, '.')}\n{t}\n" for a, b, t in cues)


def whisper(cues):
    segs = [{"id": i, "start": a, "end": b, "text": " " + t} for i, (a, b, t) in enumerate(cues)]
    return json.dumps({"text": " ".join(t for _, _, t in cues), "segments": segs}, indent=1) + "\n"


def csv_rows(header, rows, sep=",", decimal="."):
    out = [header]
    for x, y in rows:
        xs, ys = f"{x:g}", f"{y:.1f}"
        if decimal != ".":
            xs, ys = xs.replace(".", decimal), ys.replace(".", decimal)
            if sep == ",":
                xs, ys = f'"{xs}"', f'"{ys}"'
        out.append(f"{xs}{sep}{ys}")
    return "\n".join(out) + "\n"


# --- an edit session in English: fillers, dead air, two restarts ---------------------------------
EDIT_EN = [
    (0.00, 2.40, "So today we are fixing the first thirty seconds."),
    (2.50, 3.10, "Um."),
    (3.90, 6.20, "So the first thing you need to do is"),
    (6.30, 6.90, "uh, so yeah"),
    (7.00, 10.40, "So the first thing you need to do is open your analytics."),
    (10.50, 13.00, "Basically."),
    (13.10, 16.00, "Look at the retention graph for your last video."),
    (17.20, 19.80, "See that drop at eight seconds? That is the hook."),
    (19.90, 20.30, "Okay."),
    (20.40, 23.50, "Most people never look at this page."),
    (23.60, 24.00, "you know"),
    (24.80, 27.90, "Most people never look at this page, and that is the problem."),
    (28.00, 31.00, "Write five hooks, score them, keep the best two."),
    (32.50, 35.00, "That is the whole method. See you next week."),
]

# --- four topics, eight cues each: chapters ------------------------------------------------------
TOPICS_EN = [
    ["First the camera and the light", "The microphone matters more than the camera",
     "Sound decides everything", "You do not need a studio"],
    ["Now editing", "I cut straight on the timeline", "I barely use transitions", "Editing takes an hour"],
    ["Next the thumbnail and the title", "The preview must read on a phone",
     "Clicks come from the title and thumbnail", "I make the thumbnail last"],
    ["Finally promotion", "The algorithm watches retention", "Recommendations bring subscribers",
     "Subscribers come from recommendations"],
]
TOPICS_RU = [
    ["Сначала поговорим про камеру и свет", "Микрофон важнее камеры", "Звук решает всё",
     "Студия для записи не нужна"],
    ["Теперь монтаж", "Склейки делаю прямо на таймлайне", "Переходы почти не использую",
     "Монтаж занимает час"],
    ["Дальше обложка и заголовок", "Превью должно читаться на телефоне",
     "Клики решают заголовок и обложка", "Обложку делаю последней"],
    ["И наконец продвижение", "Алгоритм смотрит на удержание", "Рекомендации приводят подписчиков",
     "Подписчики приходят из рекомендаций"],
]


def topic_cues(topics, section_pause):
    """Eight 3-second cues per topic, 0.2 s between cues, `section_pause` extra between topics."""
    cues, t = [], 0.0
    for sents in topics:
        for i in range(8):
            cues.append((round(t, 3), round(t + 3, 3), sents[i % 4] + "."))
            t += 3.2
        t += section_pause
    return cues


# --- retention curves ----------------------------------------------------------------------------
def curve_pct():
    """101 points on a percentage axis: a hook drop, a slide, cliffs at 35% and 62%."""
    rows, y = [], 100.0
    for x in range(101):
        if x == 0:
            y = 100.0
        elif x <= 10:
            y -= 2.8
        else:
            y -= 0.3
            if x == 35:
                y -= 4.0
            if x == 62:
                y -= 3.0
        rows.append((x, round(y, 1)))
    return rows


def curve_seconds():
    """61 points on a seconds axis (a 600 s video): hook drop, slide, cliffs at 200 s and 410 s."""
    rows, y = [], 100.0
    for i in range(61):
        x = i * 10
        if x == 0:
            y = 100.0
        elif x <= 30:
            y -= 10.0
        else:
            y -= 0.35
            if x == 200:
                y -= 5.0
            if x == 410:
                y -= 4.0
        rows.append((x, round(y, 1)))
    return rows


def long_transcript():
    """A cue every 5 seconds for 600 s. The lines around the two cliffs say something specific."""
    special = {195: "Quick word from our sponsor before we continue.",
               200: "This part of the video is brought to you by our sponsor.",
               405: "Let me give you some background on my setup first.",
               410: "It started back in college when I bought my first camera."}
    cues = []
    for t in range(0, 600, 5):
        cues.append((float(t), t + 4.8, special.get(t, f"We keep going with point {t // 5 + 1}.")))
    return cues


# --- swipe input ---------------------------------------------------------------------------------
def swipe_en():
    def v(ch, title, views, n):
        return {"channel": ch, "title": title, "views": views,
                "url": f"https://www.youtube.com/watch?v=test{ch[:1]}{n:03d}", "duration": 600}
    rows = []
    small = [("How I film my videos", 4000), ("Camera review", 5200), ("Desk tour", 4800),
             ("Q and A", 5100), ("97% of creators quit before video 30", 51000), ("Vlog day", 6100)]
    mid = [("My editing setup", 30000), ("Lighting on a budget", 28000),
           ("I let an AI run my channel for 30 days", 120000), ("Studio update", 31000),
           ("Answering comments", 29000), ("Everyone says post daily. They are wrong", 95000)]
    big = [("Weekly news", 400000), ("Review roundup", 410000), ("Live recap", 390000),
           ("Podcast clip", 420000), ("Claude vs ChatGPT: which one wins?", 900000)]
    thin = [("Only video", 1000), ("Second video", 90000)]
    for ch, vids in [("Tiny Tutorials", small), ("Mid Channel", mid), ("Big Channel", big), ("Thin", thin)]:
        rows += [v(ch, t, n, i) for i, (t, n) in enumerate(vids)]
    return rows


# --- Russian inputs for the known-issue tests ----------------------------------------------------
EDIT_RU = [
    (0.00, 2.00, "Ну короче смотри, сегодня про монтаж."),
    (2.10, 3.00, "Эээ..."),
    (3.90, 5.50, "Я покажу как я монтирую"),
    (5.60, 6.00, "ну"),
    (6.10, 8.50, "Я покажу как я монтирую ролики за час."),
    (8.60, 11.00, "Вот этот файл, типа, главный."),
]

# The exact shape YouTube's automatic captions have, including the lines that hold one space
# ("{SP}" below) - editors like to trim those, so they are written in explicitly.
AUTO_VTT_RU = """WEBVTT
Kind: captions
Language: ru

00:00:00.160 --> 00:00:02.869 align:start position:0%
{SP}
ну<00:00:00.400><c> короче</c><00:00:00.880><c> смотри</c><00:00:01.360><c> сегодня</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
ну короче смотри сегодня
{SP}

00:00:02.879 --> 00:00:05.990 align:start position:0%
ну короче смотри сегодня
про<00:00:03.120><c> монтаж</c><00:00:03.600><c> роликов</c>

00:00:05.990 --> 00:00:06.000 align:start position:0%
про монтаж роликов
{SP}

""".replace("{SP}", " ")

# title -> the formula a Russian reader would name. Used by the swipe known-issue test.
SWIPE_RU = [
    ("Все говорят снимать каждый день. Это ошибка", "Contrarian Flip"),
    ("Я снимал видео 30 дней подряд", "I Tried It"),
    ("Почему ваши ролики никто не смотрит?", "The Question"),
    ("Не загружай видео, пока не проверишь это", "The Warning"),
    ("Монтаж против нейросети: кто быстрее", "The Comparison"),
    ("5 ошибок начинающих блогеров", "The List"),
    ("Этот канал вырос с 400 до 200 000 за полгода", "Someone Else's Result"),
]


def ret_ru_rows():
    """Percentage axis. Hook leak by design is exactly 19.5 points (100 -> 80.5 inside 10%)."""
    rows = [(0, 100.0), (5, 90.0), (10, 80.5)]
    y = 80.5
    for x in range(15, 101, 5):
        y -= 1.5
        rows.append((x, round(y, 1)))
    return rows


def main():
    write(os.path.join(EN, "edit_en.srt"), srt(EDIT_EN))
    write(os.path.join(EN, "edit_en.vtt"), vtt(EDIT_EN))
    write(os.path.join(EN, "edit_en_whisper.json"), whisper(EDIT_EN))
    write(os.path.join(EN, "chapters_en.srt"), srt(topic_cues(TOPICS_EN, 0.8)))
    write(os.path.join(EN, "chapters_en_flat.srt"), srt(topic_cues(TOPICS_EN, 0.0)))
    write(os.path.join(EN, "retention_en_pct.csv"),
          csv_rows("Video position (%),Audience retention (%)", curve_pct()))
    write(os.path.join(EN, "retention_en_seconds.csv"),
          csv_rows("Video position (seconds),Audience retention (%)", curve_seconds()))
    write(os.path.join(EN, "long_en.srt"), srt(long_transcript()))
    write(os.path.join(EN, "swipe_en.json"), json.dumps(swipe_en(), indent=1) + "\n")

    write(os.path.join(RU, "edit_ru.srt"), srt(EDIT_RU))
    write(os.path.join(RU, "auto_ru.vtt"), AUTO_VTT_RU)
    write(os.path.join(RU, "chapters_ru_flat.srt"), srt(topic_cues(TOPICS_RU, 0.0)))
    write(os.path.join(RU, "retention_ru_comma.csv"),
          csv_rows("Позиция в видео (%),Удержание аудитории (%)", ret_ru_rows(), ",", ","))
    write(os.path.join(RU, "retention_ru_semicolon.csv"),
          csv_rows("Позиция в видео (%);Удержание аудитории (%)", ret_ru_rows(), ";", ","))
    write(os.path.join(RU, "swipe_ru.json"), json.dumps(
        [{"channel": "Канал", "title": t, "views": 50000, "expected_formula": f} for t, f in SWIPE_RU]
        + [{"channel": "Канал", "title": f"Обычный ролик {i}", "views": 5000} for i in range(8)],
        ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
