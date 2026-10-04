---
name: yt-script
description: >-
  Write a YouTube video script from a raw idea - hook options off 21
  formulas, scored, then the full spoken script with the retention beats
  marked. Use whenever the user wants a video script, a hook, an opening
  line, "what should I say", "write my next video", or is about to record
  and does not have the first fifteen seconds yet. Also for Russian
  requests: "напиши сценарий для YouTube", "придумай хук", "начало
  ролика", "что сказать в первые секунды", "сценарий для видео".
---

# yt-script

One idea into a script somebody finishes.

The tools in this folder actually run: `hookscore.py` scores hooks and `aitells.py` finds
machine-written stamps. Use them. Do not eyeball the hook.

```bash
python3 "${CLAUDE_SKILL_DIR}/hookscore.py" hooks.txt              # rank your hook options
python3 "${CLAUDE_SKILL_DIR}/hookscore.py" --hook "one line"      # score a single one
```

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

## The shape

**The first 15 seconds is the whole job.** It does three things or the video leaks: confirm the
click the title promised, open a question the viewer cannot close, and prove the payoff exists.

1. **Hook.** Write FIVE against [the 21 formulas](hooks.json) and run them through `hookscore.py`.
   The score is a filter: compare the five with each other, drop the lowest-scoring ones (and any
   that opens with a greeting or a channel intro), and use the "weakest" line to fix the rest. Do
   not drop a variant for its band word alone: in English WEAK / WORKABLE / STRONG use the
   original's thresholds, which put most good hooks in WEAK; in Russian there is no band word,
   because the fitted cut failed on held-out hooks. Then choose the
   best two of what remains yourself, and for each say in one short line which formula it uses and
   why it is strong for this idea. Show the user both hooks with their score and that line. Never
   hand over one hook. Never present the score as a forecast of views: it filters out weak
   openings and says what to fix, nothing more.
2. **The turn** (0:15-0:45). Say what the video is going to do, in one sentence, and start doing it.
   No channel intro, no "before we get started", no subscribe pitch. Those are the single most
   common cause of the 0:30 cliff.
3. **The body.** One idea per beat. Mark each beat with what is ON SCREEN, not just what is said -
   a talking head with nothing to look at is a podcast.
4. **The payoff.** Deliver the thing the hook promised, explicitly, and say that you are delivering
   it: "that is the prompt, it is in the description".
5. **The close.** One ask. Not three.

## What to hand back

- the two best hooks with their scored panels and one line each on why you chose them
- the script, beat by beat, with `[ON SCREEN: ...]` on every beat
- the runtime estimate at the pace in the voice profile, 150 words per minute if it has none
- one line naming which formula the winning hook used and why it fits this idea

## Before you show it: the AI-tell check

Run `aitells.py` (in this folder) on every beat of the script and both hooks before the user sees anything:

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
- Spoken Russian: one thought per sentence, short sentences, words a person says rather than
  writes. Use the author's own words from the profile where they fit naturally - one or two a minute,
  never a pile of them.
- Score the five hooks with `hookscore.py` (Russian mode) and name formulas by their Russian names
  (`name_ru` in `hooks.json`). The score filters out weak openings and says what to fix; the choice
  of the best two is yours, with one line on formula and reason each. Never call it a forecast.
- Runtime: words divided by the pace in the profile. Without one, 150 words a minute - the pace
  measured on 226 Russian YouTube openings (37.6 words in 15 seconds).
- Run `aitells.py` on the hooks and the script and rewrite every stamp before showing anything.

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
