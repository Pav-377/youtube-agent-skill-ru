---
name: yt-package
description: >-
  Write and lint the title and thumbnail for a YouTube video as one
  pairing, checking truncation, duplication and vagueness before publish.
  Use for "title ideas", "what should I call this", "thumbnail text", "my
  CTR is bad", packaging, or any request to rename or repackage an
  existing video. Also for Russian requests: "придумай название и
  обложку", "текст на обложку", "название для ролика", "низкий CTR",
  "переупакуй видео".
---

# yt-package

The title and the thumbnail are ONE unit. Writing them separately is why most packaging fails: the
thumbnail repeats the title, and half the click surface says the same thing twice.

```bash
python3 "${CLAUDE_SKILL_DIR}/title.py" --title "..." --thumb "AI RAN IT"
python3 "${CLAUDE_SKILL_DIR}/title.py" --title "..." --thumb "AI RAN IT" --thumb-small "for 30 days"   # big text + small caption
python3 "${CLAUDE_SKILL_DIR}/title.py" titles.txt            # one per line, ranked
```

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

## Rules the tool enforces, and why

- **60 characters** is where desktop search truncates, **40** is a mobile home feed. Both are
  reported because they fail differently: a desktop cut loses the tail, a mobile cut can lose the
  subject.
- **The thumbnail must not repeat the title.** Different words, same promise.
- **Three meaningful words on the big thumbnail text.** At feed size a fourth word starts to smear:
  four or five gets a hint to shorten, six or more a warning. Small words ("in", "the", "и", "на")
  do not count. A small caption under the big text (`--thumb-small`) is checked on its own: up to six
  meaningful words, and it must not repeat the title either. Everything here is a warning, never a
  block.
- **A number, a name or a date** beats every adjective available to you.
- **Two all-caps words is the ceiling** before a title reads as spam.

## Write ten, keep two

Generate ten titles, run them all through `title.py`, show the user the top three with their scores
and the specific issue on each. For the winner, write the thumbnail brief: the expression, the
framing, the three words, and what the background has to do to hold contrast at feed size.

## Before you show it: the AI-tell check

Run `aitells.py` (in this folder) on the titles, the thumbnail text and the thumbnail brief before the user sees anything:

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
- `title.py` checks Russian titles: repeats between title and thumbnail by word form (монтаж and
  МОНТАЖА are one word), Russian stop words, caps, Russian clickbait (ШОК, вы не поверите, до слёз),
  the meaningful-word count of the big thumbnail text and of the small caption.
- Write titles the way Russian viewers search and talk. Do not use clickbait unless the user asks
  for it and accepts the warning.
- Run `aitells.py` on the titles and the thumbnail brief before showing them.

## Running the tools

The scripts sit next to this SKILL.md. `${CLAUDE_SKILL_DIR}` in the commands is this skill's folder:
Claude Code shows it as the skill's base directory; on claude.ai it is the folder this SKILL.md was
read from, so put that path in if the shell does not know the variable. If `python3` is not found
(Windows), run the same command with `python`. The scripts need Python 3.9 or newer and nothing
else, read and write only the files you give them, and never touch the network.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
