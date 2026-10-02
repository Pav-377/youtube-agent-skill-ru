---
name: yt-script
description: >-
  Write a YouTube video script from a raw idea - hook options off 21
  formulas, scored, then the full spoken script with the retention beats
  marked. Use whenever the user wants a video script, a hook, an opening
  line, "what should I say", "write my next video", or is about to record
  and does not have the first fifteen seconds yet.
---

# yt-script

One idea into a script somebody finishes.

Two tools live in this folder and both actually run. Use them. Do not eyeball the hook.

```bash
python3 hookscore.py hooks.txt              # rank your hook options
python3 hookscore.py --hook "one line"      # score a single one
```

## Before you write

1. Read `~/.claude/youtube/voice.md` if it exists. That is the user's voice profile: how they talk
   on camera, the words they never use, who they are talking to, what they will not claim. If it
   does not exist, ask for **three of their own videos**, read or transcribe them, infer the voice,
   and write the file. A script in the wrong voice is worse than no script, because they have to
   read it out loud.
2. Never invent a number, a result or a source. If a figure would strengthen it and you do not have
   one, ask for it or write the line without it.

## The shape

**The first 15 seconds is the whole job.** It does three things or the video leaks: confirm the
click the title promised, open a question the viewer cannot close, and prove the payoff exists.

1. **Hook.** Write FIVE against [the 21 formulas](hooks.json) and run them through `hookscore.py`.
   The score is a filter: drop the variants it marks WEAK and use its "weakest" line to fix the
   rest. Then choose the best two of what remains yourself, and for each say in one short line
   which formula it uses and why it is strong for this idea. Show the user both hooks with their
   score and that line. Never hand over one hook. Never present the score as a forecast of views:
   it filters out weak openings and says what to fix, nothing more.
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
- the runtime estimate at 150 words per minute
- one line naming which formula the winning hook used and why it fits this idea

## Before you show it: the AI-tell check

Run `aitells.py` (in this folder) on every beat of the script and both hooks before the user sees anything:

```bash
python3 aitells.py --text "..."      # or a file, paragraphs separated by an empty line
```

Rewrite every **stamp** it reports - the "not X, but Y" contrast, the canned linking phrase, the
lead-in question, the slogan-like parallel, the triads one after another - in plain words, and act
on the **speech** notes (split a sentence that cannot be said in one breath). Run it again until no
stamp is left. It only finds; the rewriting is yours, and it must sound like the user's voice
profile, not like a cleaned-up version of you.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**
