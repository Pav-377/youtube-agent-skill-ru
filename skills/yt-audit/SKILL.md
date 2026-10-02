---
name: yt-audit
description: >-
  Audit a YouTube channel end to end - packaging, consistency, the first
  fifteen seconds, and what to fix first. Use for "audit my channel", "why
  isn't my channel growing", "review my videos", or a pasted channel URL.
  Also for Russian requests: "разбери мой канал", "аудит канала", "почему
  канал не растёт".
---

# yt-audit

An audit that lists twenty problems is a way of avoiding the one that matters. This ends in ONE fix.

## Before you write

1. Read the user's voice profile first: `~/.claude/youtube/voice.md` in Claude Code, or the profile
   the user put into this project's instructions or pasted into the chat (claude.ai and Claude
   Desktop have no `~/.claude`). It says how they talk on camera, whether they say «ты» or «вы» to
   the viewer, their pace in words per minute, the words that are theirs, the words they never use,
   who they are talking to, what they will not claim. If there is no profile, ask for **three of
   their own videos** (links or transcripts), infer the voice, and hand the profile back as ready
   text following `voice_template.ru.md` (Russian) or `voice_template.md` (English) in this
   folder. In Claude Code, save it yourself to `~/.claude/youtube/voice.md` (create the folder; if
   the file already exists, show the changes and ask before replacing it). Never write the profile
   into the plugin or skill folder, and never tell the user to fill in the template there: an
   update replaces that folder and the profile is lost. On claude.ai and Claude Desktop, hand it
   back as text for the project instructions. A script in the wrong voice is worse than no script, because they have
   to read it out loud.
2. Never invent a number, a result or a source. If a figure would strengthen it and you do not have
   one, ask for it or write the line without it.

## What to look at, in this order

1. **The last ten titles, as a set.** Read them as a list, the way the channel page shows them. Do
   they promise different things? Run them through `title.py` (in this folder). A channel where every
   title is the same shape has a format problem, not a title problem.
2. **The thumbnails, at feed size.** Shrink them. What survives? If three of them are unreadable at
   that size, that is the fix and nothing else matters yet.
3. **The first fifteen seconds of the three most recent.** Transcribe them and score with
   `hookscore.py` (in this folder). This is where most channels lose.
4. **Upload rhythm.** Not frequency - CONSISTENCY. Six videos in one week and then nothing for a
   month is worse than one a fortnight forever.
5. **The retention shape**, if they can export it. `/yt-retention`.

## What to hand back

- The single biggest fix, named, with what to do this week.
- Three things that are already working, so they do not break them. Be specific; "your energy is
  good" is not an observation.
- What NOT to do yet, and why.

Never open an audit with praise you do not mean, and never end one with a list of twenty things.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The tools detect Russian on their own (`--lang ru` forces it) and report in Russian.
- `title.py` and `hookscore.py` run in Russian mode on Russian titles and openings.
- The hook score is a filter for weak openings, not a forecast. Never tell the user a video will do
  well because its hook scored high: on 226 real Russian openings, hits and misses scored the same.

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
