---
name: yt-seo
description: >-
  Write the description, tags and search-facing text for a YouTube video,
  aimed at the query a real person types. Use for "write my description",
  "tags", "SEO", "help this video get found", "nobody is finding this".
  Also for Russian requests: "напиши описание", "теги для видео", "SEO для
  YouTube", "чтобы видео находили в поиске".
---

# yt-seo

Search is a smaller lever than packaging and a bigger one than people think for evergreen videos.
For a video aimed at the subscriber feed, say so and spend the effort on `/yt-package` instead.

## Before you write

1. Read the user's voice profile first: `~/.claude/youtube/voice.md` in Claude Code, or the profile
   the user put into this project's instructions or pasted into the chat (claude.ai and Claude
   Desktop have no `~/.claude`). It says how they talk on camera, whether they say «ты» or «вы» to
   the viewer, their pace in words per minute, the words that are theirs, the words they never use,
   who they are talking to, what they will not claim. If there is no profile, ask for **three of
   their own videos** (links or transcripts), infer the voice, and hand the profile back as ready
   text following `voice_template.ru.md` (Russian) or `voice_template.md` (English) in this
   folder, saying where to keep it: `~/.claude/youtube/voice.md` in Claude Code, the project
   instructions on claude.ai. A script in the wrong voice is worse than no script, because they have
   to read it out loud.
2. Never invent a number, a result or a source. If a figure would strengthen it and you do not have
   one, ask for it or write the line without it.

## The description

- **The first lines are what people see first,** above "...more" - YouTube Help says to use them
  to describe the video. Say what the video gives them, in the words they would have typed.
- Then the link or the resource, if there is one, so it is above the fold.
- Then chapters (`/yt-chapters` writes them).
- Then the long version: what is covered, who it is for, what it assumes.

## Tags, honestly

Tags are a weak signal and YouTube has said so: its Help calls their role in discovery minimal. Use them for disambiguation - spellings, the tool
names, the abbreviations people actually type - and stop. Fifteen is plenty. A wall of tags is not
a strategy and stuffing unrelated ones is against the terms.

## The query test

Before handing anything over, write the three search queries this video should win, and check the
title and first two description lines contain the words in those queries. If they do not, the
problem is the title, not the description.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- Write the description in Russian with the words Russian viewers actually type - often plain ones:
  «как», «что такое», «за 5 минут», «бесплатно».
- Tags: YouTube Help says they play a minimal role in discovery. Use a few for spellings and
  transliterations people type (нейросеть / нейронка, ChatGPT / чат гпт); excessive tags break
  YouTube's spam policy.
- The description holds up to 5000 characters; the first lines are what viewers see first.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
