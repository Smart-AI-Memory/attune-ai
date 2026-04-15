# Discord Post: Attune AI v6.0.0 + attune-author 0.3.5

## Hook post (under 2000 chars)

**Attune AI v6.0.0 — AI-powered user assistance for Claude Code**

Two releases today, two different use cases:

**attune-ai** is a framework for building AI-powered
user assistance features in Claude Code. It gives
you 14 auto-triggering skills, 41 MCP tools, and a
workflow engine you can compose into anything from
security audits to onboarding guides to interactive
tutors. We used it to build attune-help (a
progressive-depth help runtime) and attune-author (a
self-maintaining documentation engine) — and you can
extend it with your own.

**attune-author** is for teams who want
context-sensitive help in their AI projects — without
writing or maintaining docs manually. Point it at
your source code and it:

- Scans your codebase and proposes a feature manifest
- Generates help at three progressive depths
  (concept → how-to → full reference)
- Detects when source files change and flags stale docs
- Regenerates with an LLM polish pass that turns code
  structure into clear, specific prose

The result: users of your project get help that
adapts to their session (ask once for an overview,
again for details, again for the full reference) and
stays accurate as the code evolves. No manual docs
maintenance.

**Which one do I want?**

Building AI-powered user assistance features with
Claude Code? → `pip install attune-ai`

Want self-maintaining, context-sensitive help for
your AI project? → `pip install attune-author`

Want both? attune-ai includes attune-author as a
dependency — install attune-ai and you get everything.

```
pip install attune-ai
```

Or as a Claude Code plugin:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

https://github.com/Smart-AI-Memory/attune-ai

## Thread reply: what's new in v6.0.0

New in attune-ai v6.0.0:

- LLM polish pass now wired into help template
  generation — all templates ship with polished
  prose instead of raw skeleton output
- MCP server works in VS Code out of the box
  (previously CLI-only)
- Staleness detection is deterministic — cache
  directories no longer corrupt the source hash
- 15,002 tests across 12 platform combos (Ubuntu,
  macOS, Windows x Python 3.10-3.13)

New in attune-author 0.3.5:

- Same staleness and sort fixes ported from
  attune-ai — both packages stay in sync
- 354 tests passing

attune-help and attune-author are the proof that
the platform works — real user-facing features built
entirely with attune-ai's workflow and MCP tools.

## Formatting notes

- Discord supports markdown but not all GFM
- Keep code blocks to triple backticks
- No tables — use lists
- Hook post is under 2000 chars
- Thread reply adds detail for people who click in
