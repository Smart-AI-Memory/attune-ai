# Discord Post: Anthropic Community

**Building a self-maintaining help system with Claude
Code + MCP**

Been working on something I think this community would
find interesting — a help system that uses Claude Agent
SDK subagents to maintain its own documentation.

The core UX is three words: **"tell me more."**

Ask about any topic and you get a concept overview. Say
"tell me more" — step-by-step task guide. Say it again —
full reference with edge cases and config. The system
tracks session state so it always picks up where you left
off.

```
"what is security audit?"  ->  concept (what + when)
"tell me more"             ->  task (how-to + examples)
"tell me more"             ->  reference (full detail)
```

557 templates across 11 types, all self-maintaining: a
5-phase pipeline where agents detect stale docs,
regenerate via Batch API (50% cost savings), and rebuild
cross-links automatically. Usage telemetry weights what
gets maintained first.

Claude Code plugin with 13 auto-triggering skills and 38
MCP tools. Try it:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Then say "what can attune do?" and "tell me more" to see
it in action. The entire help system runs on your Claude
subscription — no API key required.

Open source, Apache 2.0:
https://github.com/Smart-AI-Memory/attune-ai

This is the first in a series where I'll cover building
knowledge bases, help systems, dynamic assistance, and
context-aware documents with Claude Code + MCP.

If you find it useful, a star on the repo goes a long
way. Would love feedback from anyone building MCP tools
or working on the "docs that stay accurate" problem.
