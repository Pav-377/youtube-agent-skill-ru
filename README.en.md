# YouTube agent for Claude

A Claude plugin with 11 commands for YouTube creators: script, title and thumbnail, edit list,
retention, Shorts and more. Works in Russian and English. The main documentation is in Russian:
[README.md](README.md).

## Commands

| Command | What it does | Example request |
| --- | --- | --- |
| `/yt-script` | Writes a script: five scored hook options, then the script in beats | "Write a script about editing on a phone" |
| `/yt-package` | Writes the title and thumbnail text, checks length, overlap and clickbait | "Title and thumbnail ideas" |
| `/yt-edit` | Builds an edit list from a transcript: pauses, hesitations, filler words, retakes | "Here are the captions. What do I cut?" |
| `/yt-retention` | Reads a YouTube Studio retention export: where viewers leave and why | "Why do people stop watching?" |
| `/yt-shorts` | Finds Shorts in a long video and writes their first lines | "Cut this into Shorts" |
| `/yt-chapters` | Writes chapters that follow YouTube's rules | "Add chapters" |
| `/yt-seo` | Writes the description and tags for search | "Write the description and tags" |
| `/yt-comment` | Sorts comments and drafts replies in the creator's voice | "Reply to my comments" |
| `/yt-plan` | Plans uploads around the time you have | "Plan my week, I have 8 hours" |
| `/yt-audit` | Audits a channel and names the one fix that matters most | "Audit my channel" |
| `/yt-viral` | Finds videos in a niche that beat their channel's usual views | "What's working in my niche" |

## Requirements

- Claude Code, or claude.ai with code execution turned on.
- Python 3.9 or newer. No third-party packages.

## Install

In Claude Code, send: "Install this plugin: {{REPO_URL}}", then open a new chat.

Or run these two commands in Claude Code:

```
/plugin marketplace add {{OWNER}}/{{REPO}}
```

```
/plugin install youtube-agent-ru@youtube-agent-skill-ru
```

For claude.ai, download the per-skill zips from {{REPO_URL}}/releases and upload each one under
Customize > Skills. Details: [docs/INSTALL.md](docs/INSTALL.md) (Russian).

## Limitations

- The plugin does not publish, edit video files or sign in to YouTube.
- The hook score filters out weak openings and says what to fix. It does not predict views.
- Russian YouTube Studio column names are not yet checked against a real export.

Full list: [docs/LIMITATIONS.md](docs/LIMITATIONS.md) (Russian).

## Licence

MIT. Based on [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) by
Jake Schincariol. The original copyright line is kept in [LICENSE](LICENSE).
