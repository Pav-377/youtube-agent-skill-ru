---
name: yt-edit
description: >-
  Turn a raw recording's transcript into an edit decision list - dead air,
  filler cues and retakes, with timecodes. Use for "edit this", "cut the
  dead space", "tighten this video", "I rambled", or any request to
  shorten footage from a transcript. Also for Russian requests: "вырежи
  паузы", "убери слова-паразиты", "где я запинаюсь", "сократи видео по
  транскрипту", "монтажный лист".
---

# yt-edit

An edit decision list from a timestamped transcript. It prints the cuts. You apply them.

```bash
python3 "${CLAUDE_SKILL_DIR}/deadair.py" transcript.srt              # srt, vtt or whisper json
python3 "${CLAUDE_SKILL_DIR}/deadair.py" transcript.srt --floor 0.35 --json
```

No transcript yet? Ask for one, or produce one first - `whisper`, `faster-whisper`, or the caption
track YouTube generates on an unlisted upload all work. Do not guess at timings.

## What it finds

- **DEAD** - gaps longer than the floor, trimmed from the MIDDLE so both sides keep a breath.
  Cutting flush against speech is what makes a tightened take sound gasping.
- **FILLER** - cues that are nothing but "um", "so yeah", "basically".
- **REPEAT** - a sentence restarted. Compared against the last cue that was actually speech, not
  the literal previous cue, because most retakes have an "um" between the two attempts.

## What it will not do

It does not touch media. It has no opinion about your B-roll. A 40% cut on the report is a 40% cut
of SPEECH, and if the video has a long silent demo in it that number is wrong - check the report
against the footage before you trust the runtime at the bottom.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The tools detect Russian on their own (`--lang ru` forces it) and report in Russian.
- `deadair.py` marks Russian hesitations (always cut), filler words (cut, or kept as live speech, with
  a reason) and stumbles, word by word. Show the CUT list and the KEEP list apart, and say that the
  kept connectors are kept on purpose.
- Words that often carry meaning (реально, прям, на самом деле, так сказать) are never cut
  automatically; mention them only if the user asks for a stricter edit.
- Exact times need word timing. Best sources, in order: 1) YouTube automatic captions
  (`yt-dlp --write-auto-subs --sub-langs ru --skip-download URL`), 2) Whisper with
  `--word_timestamps True`, 3) an .srt, where times are approximate (marked ≈) - say so.
- The profile wins: its "words to keep" stay even when the tool marks them CUT; its "fillers to
  remove always" go even at the start of a phrase.

## Running the tools

The scripts sit next to this SKILL.md. `${CLAUDE_SKILL_DIR}` in the commands is this skill's folder:
Claude Code shows it as the skill's base directory; on claude.ai it is the folder this SKILL.md was
read from, so put that path in if the shell does not know the variable. If `python3` is not found
(Windows), run the same command with `python`. The scripts need Python 3.9 or newer and nothing
else, read and write only the files you give them, and never touch the network.

If neither command works - "not found", "Python was not found" from the Windows Store stub, exit
code 9009, or a version older than 3.9 - stop and tell the user in their language, in plain words,
that the tool did not run because Python is missing, and point them to the "Если нет Python"
section of docs/INSTALL.md (Russian) or https://www.python.org/downloads/ . Do not score, count or
lint by eye and present it as the tool's result; if they want to go on without Python, say clearly
that what follows is your own judgement, not the tool's.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
