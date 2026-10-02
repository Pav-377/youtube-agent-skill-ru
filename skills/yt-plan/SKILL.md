---
name: yt-plan
description: >-
  Plan a week or a month of YouTube uploads - what to post, when, and in
  what order, sized to the creator's actual capacity. Use for "plan my
  week", "content calendar", "what should I post", "I have no idea what to
  make next". Also for Russian requests: "контент-план на неделю", "план
  публикаций", "что снять дальше", "расписание роликов".
---

# yt-plan

A plan that does not fit the week is a list of regrets. Ask two questions before writing anything:
**how many hours do you actually have**, and **what is already half-made**.

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

## The shape of a week

- **One anchor.** The video the week is for. It gets the most time and it goes out on the day the
  channel's own analytics say is best - ask for that, do not assume Tuesday.
- **One cheap one.** Built from something that exists: a clip, a reaction, a follow-up to the
  comment that got the most replies last week.
- **Shorts from the anchor.** Three, cut from the long video, not written separately. `/yt-shorts`
  finds them.

Three uploads on a seven-day week, not seven. A plan that posts daily is not a plan anyone
recognises, and the empty days are what make the filled ones survive a bad week.

## What to hand back

A table: day, format, working title, the one sentence it promises, and what already exists for it.
Then the honest line at the bottom - how many hours this costs, and what to drop first if the week
goes wrong.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The table in Russian: День, Формат, Рабочее название, Обещание, Что уже есть.
- Do not assume holidays or audience habits; ask for the channel's own best days.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
