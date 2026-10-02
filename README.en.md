# The YouTube agent skill — Russian-language version

Eleven Claude skills for YouTube creators, working in Russian and English: script, title and
thumbnail, edit list, retention, Shorts, chapters, description, comment replies, a weekly plan, a
channel audit and a virality engine. Free, MIT.

This is a fork of [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) by
Jake Schincariol. The ideas, the 21 hook formulas and the tools are his; this version adds Russian
and fixes what got in the way. The main README is in Russian: [README.md](README.md).

**Nothing gets published by the plugin.** It writes and checks. You upload.

## Install

```
/plugin marketplace add Pav-377/youtube-agent-skill-ru
/plugin install youtube-agent-ru@youtube-agent-skill-ru
```

For claude.ai, download the per-skill zips from the latest GitHub Release and upload them under
Customize > Skills (code execution must be on). Details in [docs/INSTALL.md](docs/INSTALL.md) (Russian).

## What changed from the original

- Russian everywhere: every script detects the language, uses Russian word lists, reports in Russian.
- Russian YouTube Studio exports (decimal comma, semicolons, Russian headers, the zip) read correctly.
- Russian filler words handled by context: hesitations always cut, connectors at the start of a
  phrase kept, meaningful uses never touched; exact word times from YouTube's automatic captions.
- New: `aitells.py`, a check for machine-written stamps in scripts, in Russian and English.
- Every skill is self-contained, so each uploads to claude.ai on its own.
- Bugs fixed, including in English mode. Everything is listed in [CHANGELOG.md](CHANGELOG.md).

The hook score filters out weak openings and says what to fix. It does not predict views: on 226 real
Russian videos, hits and misses scored the same. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Licence

MIT, like the original. The original copyright line is kept in [LICENSE](LICENSE).
