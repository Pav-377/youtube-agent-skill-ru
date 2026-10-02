---
name: yt-shorts
description: >-
  Find the Shorts hiding inside a long video and write them, using the
  transcript to pick self-contained moments. Use for "cut this into
  shorts", "clip this", "repurpose this video", "what should I clip". Also
  for Russian requests: "нарежь шортсы", "сделай Shorts из видео", "что
  вырезать в короткие ролики".
---

# yt-shorts

A Short cut out of a long video is not a clip of the best moment. It is a moment that **survives
without the video around it**, which is a much smaller set.

## Picking

Read the transcript and find spans of 20-55 seconds where all three are true:

1. It opens on a complete thought. If the first sentence needs the previous minute, it is not a Short.
2. There is a turn in it - a claim, then something that complicates or proves it.
3. It ends on a line, not a trail-off.

Rank the candidates and show the user the top five with their timecodes and first line, so they can
reject one without reading the whole transcript.

## Writing each one

- **A NEW first line.** The long video's line assumes context this viewer does not have. Write the
  replacement and run it through `hookscore.py` (in this folder). Compare the candidate lines by
  score with each other; the English band word alone (WEAK and so on) is not a reason to drop one,
  and the Russian report has no band word at all.
- **On-screen text for the first two seconds**, different words from the spoken line.
- **A loop point**: what the last line sets up so the first line answers it.
- Vertical framing note - what gets cropped out of a 16:9 frame and whether that matters.

## Before you show it: the AI-tell check

Run `aitells.py` (in this folder) on the new first line and the on-screen text of each Short before the user sees anything:

```bash
python3 "${CLAUDE_SKILL_DIR}/aitells.py" --text "..."      # or a file, paragraphs separated by an empty line
```

Rewrite every **stamp** it reports - the "not X, but Y" contrast, the canned linking phrase, the
lead-in question, the slogan-like parallel, the triads one after another - in plain words, and act
on the **speech** notes (split a sentence that cannot be said in one breath). Run it again until no
stamp is left. It only finds; the rewriting is yours, and it must sound like the user's voice
profile, not like a cleaned-up version of you.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The tools detect Russian on their own (`--lang ru` forces it) and report in Russian.
- Pick the spans in the Russian transcript. Write the new first line in spoken Russian and score it
  with `hookscore.py`; the score filters out weak openings, it does not promise views.
- On-screen text in Russian, about five words at most, different from the spoken line.
- Run `aitells.py` on the first lines and the on-screen text before showing them.

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
