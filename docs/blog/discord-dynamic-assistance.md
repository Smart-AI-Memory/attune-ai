# Discord Post: Help That Knows Who's Reading

**Part 4: Context-aware documents that adapt without
configuration**

Static docs show the same thing to everyone. Attune AI's
help system adapts to four kinds of context:

**1. Audience adaptation** — same template, three outputs.
Claude Code gets concise hints (~500 chars). CLI gets
Rich-formatted colored panels. Marketplace gets full
markdown with frontmatter. No rewriting — just strategic
inclusion/exclusion per audience.

**2. Precursor warnings** — help before you need it.
Editing a `.py` file? The engine maps the extension to
tags (python, imports, testing) and surfaces relevant
warnings from past bugs:

```
Precursor warnings:
  - Adding logger before imports triggers E402
  - config.py alongside config/ creates duplicate module
```

**3. Progressive depth** — session state in three fields:

```json
{"last_topic": "security-audit", "depth_level": 1, "timestamp": 1743580800}
```

Ask again → depth increments. New topic → resets to 0.
4-hour TTL → resets if you've been away. Simple rules,
no configuration.

**4. Usage weighting** — templates linked to expensive,
frequently-used workflows get maintained first. The
system measures what matters instead of guessing.

The design principle: **adapt to context without asking
the user to configure anything.** Audience detected, not
selected. Warnings surfaced, not searched for. Depth
escalates, not navigates.

Try it:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Runs on your Claude subscription — no API key required.

Part 4 of a series on building knowledge bases and
context-aware docs with Claude Code. Star the repo if
useful: https://github.com/Smart-AI-Memory/attune-ai

Next: the 5-phase maintenance pipeline that keeps it
all accurate.
