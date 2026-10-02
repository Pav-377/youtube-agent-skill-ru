#!/usr/bin/env python3
"""make_demo_files.py - write the demo inputs and the expected outputs in demo/.

    python demo/make_demo_files.py          # inputs + expected/*.txt (this version)
    python demo/make_demo_files.py --check  # exit 1 if an expected output no longer matches

Every input is invented for the demo: no real channel, transcript or Studio export.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")

P1 = ("Claude только что уничтожил YouTube. Теперь его можно подключить к каналу, и он будет вести "
      "весь твой контент за тебя.")

# (line text, pause in seconds before the line). Words get 0.32 s each; a YouTube-style caption file
# carries a time for every word, which is what makes the cut list exact.
SPEECH = [
    ("Ну, смотри. Сегодня покажу, как я монтирую", 0.0),
    ("ролики на телефоне. Э-э... короче, типа, всё", 0.0),
    ("начинается с черновика. Вот этот файл — исходник.", 0.0),
    ("Я я открываю его в приложении.", 0.0),
    ("Мм, сначала убираю паузы.", 1.6),
    ("Это значит, что ролик станет короче на треть.", 0.0),
    ("В общем, монтаж занимает час, ну, как бы,", 0.0),
    ("если не отвлекаться. Это реально удобно.", 0.0),
    ("Я покажу как я ставлю", 0.9),
    ("Я покажу, как я ставлю музыку под голос.", 0.4),
]

SCRIPT_AI = """Давайте разберёмся, почему ваши ролики не досматривают. В современном мире внимание зрителя — это главная валюта.

Знаешь, почему? Потому что первые секунды решают всё. Это не про монтаж, а про смысл.

Важно понимать, что обложка играет ключевую роль. Хорошая обложка привлекает, удерживает и продаёт.

Идея — твоя, исполнение — нейросети.
"""

RETENTION = [(0, "100,0"), (5, "90,0"), (10, "80,5"), (20, "74,0"), (30, "70,0"), (40, "67,5"), (50, "61,0"),
             (60, "58,0"), (70, "55,5"), (80, "52,0"), (90, "49,0"), (100, "45,0")]

TITLES = [
    ("Канал про монтаж", [("Монтаж на телефоне за 10 минут", 61000), ("Мой рабочий стол", 6200),
                          ("Обзор нового приложения", 5800), ("Ответы на вопросы", 6100),
                          ("Все говорят: нужен ноутбук. Это миф", 48000), ("Влог со съёмок", 5900)]),
    ("Нейросети для авторов", [("5 нейросетей для обложек", 120000), ("Новости недели", 24000),
                               ("Стрим: отвечаю на вопросы", 21000), ("Обзор обновления", 26000),
                               ("Почему твои ролики не досматривают?", 95000), ("Разбор комментариев", 23000)]),
    ("Блог о блоге", [("Я снимал 30 дней подряд", 41000), ("Как я веду канал", 8000),
                      ("Мой путь на YouTube", 7500), ("Отвечаю подписчикам", 8200),
                      ("Ошибка, из-за которой уходят зрители", 9000)]),
]


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def vtt():
    """YouTube's automatic-caption shape: every word timed, each line shown once with its timing."""
    out, t = ["WEBVTT", "Kind: captions", "Language: ru", ""], 0.0
    for line, pause in SPEECH:
        t += pause
        words = line.split()
        start, timed = t, words[0]
        for w in words[1:]:
            t += 0.32
            timed += f"<{ts(t)}><c> {w}</c>"
        t += 0.32
        out += [f"{ts(start)} --> {ts(t)} align:start position:0%", " ", timed, ""]
    return "\n".join(out) + "\n"


def write(name, text):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def inputs():
    write("transcript_ru.vtt", vtt())
    write("script_ai.txt", SCRIPT_AI)
    write("retention_ru.csv", "Позиция в видео (%),Удержание аудитории (%)\n" +
          "".join(f'{x},"{y}"\n' for x, y in RETENTION))
    rows = [{"channel": ch, "title": t, "views": v} for ch, vids in TITLES for t, v in vids]
    write("titles_ru.json", json.dumps(rows, ensure_ascii=False, indent=1) + "\n")


CASES = [
    ("1_hook.txt", "yt-script/hookscore.py", ["--hook", P1]),
    ("2_fillers.txt", "yt-edit/deadair.py", ["transcript_ru.vtt"]),
    ("3_retention.txt", "yt-retention/retention.py", ["retention_ru.csv"]),
    ("4_aitells.txt", "yt-script/aitells.py", ["script_ai.txt"]),
    ("5_swipe.txt", "yt-viral/swipe.py", ["titles_ru.json", "--min", "2"]),
]


def run(script, args, skills=SKILLS):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0")
    p = subprocess.run([sys.executable, os.path.join(skills, script)] + args, cwd=HERE, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    return p.stdout


def main():
    os.makedirs(os.path.join(HERE, "expected"), exist_ok=True)
    if "--check" in sys.argv:
        bad = []
        for name, script, args in CASES:
            with open(os.path.join(HERE, "expected", name), encoding="utf-8", newline="") as fh:
                if fh.read() != run(script, args):
                    bad.append(name)
        for b in bad:
            print(f"  demo/expected/{b} is out of date - run python demo/make_demo_files.py")
        sys.exit(1 if bad else 0)
    inputs()
    for name, script, args in CASES:
        with open(os.path.join(HERE, "expected", name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(run(script, args))
        print(f"  demo/expected/{name}")


if __name__ == "__main__":
    main()
