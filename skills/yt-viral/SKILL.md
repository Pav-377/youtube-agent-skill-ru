---
name: yt-viral
description: >-
  Find what is actually working in the user's niche on YouTube and rank it
  by how far each video beat its own channel, then name the formula. Use
  for "what's working right now", "find viral videos in my niche", "why
  did this blow up", competitor research, or a swipe file. Also for
  Russian requests: "найди идеи у конкурентов", "что сейчас залетает в
  моей нише", "почему это видео взлетело", "выбросы по просмотрам".
---

# yt-viral

Raw view counts rank channel size, not ideas. This ranks by **multiple over each channel's own
median**, which is the only version of the question that is about the video.

```bash
python3 "${CLAUDE_SKILL_DIR}/swipe.py" collected.json --min 2.0
```

## Collecting the input

You need at least **four videos per channel** or a median means nothing, and the tool will skip the
channel and tell you it did. Collect them however the user prefers - `yt-dlp --flat-playlist -J`
against a channel URL is the fastest, the public page works, a manual list works.

```json
[{"channel":"...","title":"...","views":412000,"url":"...","duration":613}]
```

**Read, do not scrape.** Public listings only, never a logged-in session, never the user's own
account credentials.

## Reading the output

The multiple is the signal. The formula line is a judgement about the TITLE, matched against
[the 21 formulas](hooks.json) - it is not a claim about why the video worked, and you
should say so when you present it.

What to hand back: the top five with their multiples, the formula each used, and the ONE structural
thing they share. Then the harder line - which of those the user could actually make this week, in
their voice, with what they have.

## Russian-language mode

When the user writes in Russian, or the material (a transcript, titles, an export) is Russian:

- Answer in Russian, in plain spoken language, without bureaucratic words (данный, является,
  осуществлять) and without machine-written stamps («не X, а Y», «давайте разберёмся», lead-in
  questions like «Знаешь, почему?»). Keep «ты» or «вы» exactly as the
  voice profile sets it, the same way from start to end.
- Take tone and format from [examples_ru.md](examples_ru.md). The examples are format samples, not
  facts: never quote their numbers or present them as real channels or real results.
- The tools detect Russian on their own (`--lang ru` forces it) and report in Russian.
- `swipe.py` reads Russian view counts (1,2 тыс., 3 млн, 200 000) and names the formula of a Russian
  title by its Russian name from `hooks.json`.
- Collecting with yt-dlp: take view counts with `--extractor-args youtube:lang=en` (with Russian
  pages a channel list can shorten "181 тыс." to 181) and titles with `youtube:lang=ru` (without it
  YouTube may hand back machine translations).
- The formula is a judgement about the title's words, not the reason the video took off. Say so.

## Running the tools

The scripts sit next to this SKILL.md. `${CLAUDE_SKILL_DIR}` in the commands is this skill's folder:
Claude Code shows it as the skill's base directory; on claude.ai it is the folder this SKILL.md was
read from, so put that path in if the shell does not know the variable. If `python3` is not found
(Windows), run the same command with `python`. The scripts need Python 3.9 or newer and nothing
else, read and write only the files you give them, and never touch the network.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
