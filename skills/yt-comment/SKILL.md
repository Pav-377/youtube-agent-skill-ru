---
name: yt-comment
description: >-
  Draft replies to YouTube comments in the creator's voice, triaged by
  which ones are worth answering. Use for "reply to my comments", "handle
  the comment section", "someone asked X", or a pasted comment thread.
  Also for Russian requests: "ответь на комментарии", "разбери
  комментарии", "что ответить зрителю", "какой комментарий закрепить".
---

# yt-comment

The comment section is a retention surface, not a chore. Replies in the first few hours are what
decide whether a thread becomes a conversation other people read.

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

## Triage first, always

Sort what the user pastes into four piles and say how many are in each before writing anything:

1. **Questions** - answer them. These are your next video's topics, so note the repeats.
2. **Corrections** - if they are right, say so plainly and thank them. Never argue a fact you
   cannot check.
3. **Praise** - reply to a few, briefly, with something specific from their comment. A wall of
   identical "thank you!" replies reads as automated because it is.
4. **Bait** - do not reply. Say so and move on. Never write a comeback, however deserved.

## Writing the reply

- Under 30 words. A long reply in a comment thread is a blog post nobody asked for.
- Answer the actual question in the first sentence.
- One question back, only when it is real.
- No emoji unless the user's own replies use them. Check their voice file.
- Never promise a video you have not agreed to make.

## The heart and the pin

Say which ONE comment to pin and why. Pin the question the most people also have, not the nicest
one. Heart generously - it costs nothing and it is visible.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- Name the four piles in Russian: Вопросы, Поправки, Похвала, Провокации.
- Reply in the author's voice. Address a commenter as the profile says, or as the commenter
  addressed the author if the profile is silent.
- Say it plainly: this skill prepares the replies; the author posts them. Nothing is published,
  hearted or pinned by the plugin.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
