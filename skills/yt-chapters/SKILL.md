---
name: yt-chapters
description: >-
  Write YouTube chapters from a transcript, validated against YouTube's
  own rules so they actually render. Use for "add chapters", "timestamps",
  "break this video into sections". Also for Russian requests: "сделай
  таймкоды", "главы для видео", "раздели ролик на части".
---

# yt-chapters

```bash
python3 "${CLAUDE_SKILL_DIR}/chapters.py" transcript.srt --target 8
```

## The rules, which are not optional

A chapter list that breaks any of these silently does not become chapters at all - the block just
sits in the description doing nothing:

- The first entry must be **00:00**.
- There must be **at least three**.
- Each must be **at least 10 seconds** long.

The tool checks all three and tells you when a list is invalid rather than letting you paste it.

## Retitle every line

`chapters.py` finds the BOUNDARIES well - it scores the pauses you actually took by how much the
vocabulary shifts across them. The titles it emits are the topic words, and they are a draft. A
chapter called "Thumbnails Titles Packaging" is a placeholder. Rewrite each one as the promise of
that section, in the user's voice, three to five words.

Chapters are also a retention diagnostic: if a section cannot be named in five words, it is two
sections or it is filler.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The tools detect Russian on their own (`--lang ru` forces it) and report in Russian.
- `chapters.py` drafts Russian chapter titles from the topic words of each section. Rewrite every
  one as a promise of three to five Russian words.
- YouTube's rules, checked against YouTube Help: the first timestamp is 00:00, there are at least
  three, and each chapter is at least 10 seconds long.

## Running the tools

The scripts sit next to this SKILL.md. `${CLAUDE_SKILL_DIR}` in the commands is this skill's folder:
Claude Code shows it as the skill's base directory; on claude.ai it is the folder this SKILL.md was
read from, so put that path in if the shell does not know the variable. If `python3` is not found
(Windows), run the same command with `python`. The scripts need Python 3.9 or newer and nothing
else, read and write only the files you give them, and never touch the network.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
