---
type: concept
name: tool-memory-and-context
tags: [memory, context, persistence]
source: plugin/skills/memory-and-context/SKILL.md
---

# Memory and Context

Every new Claude Code session starts with a blank slate.
Memory and context bridges that gap — it stores notes,
preferences, project decisions, and working state that
persist across sessions. The next session picks up where
the last one left off without you repeating yourself.

## What it does

| Operation | What it does | Persists? |
|-----------|-------------|-----------|
| **Store** | Save a note, decision, or pattern with a key | Yes, across sessions |
| **Recall** | Retrieve a specific memory by key | -- |
| **Search** | Find memories matching a query | -- |
| **Forget** | Remove a memory you no longer need | Permanent deletion |
| **Context** | Store temporary state for this session only | No, session only |

## When you'd use it

Store a debugging pattern you figured out so you don't
have to rediscover it next week. Save a project convention
("we use snake_case for file names") so every session
follows the same rules. Record an architecture decision
so future sessions know why you chose SQLite over
Postgres.

Good candidates for memory:

- Debugging patterns that took effort to figure out
- Project conventions and naming rules
- Architecture decisions and their rationale
- Working state ("I'm in the middle of refactoring auth")
- Team preferences ("Patrick prefers concise output")

## How it works

You describe what you want to remember or find, and the
skill asks clarifying questions before storing or
searching. Everything runs on your Claude subscription
with no API key or extra cost.

```
remember that we use pytest-asyncio for all async tests
```

The skill stores that note with a key you can recall
later. When you start a new session and need that
context:

```
what testing framework do we use for async?
```

The skill searches your stored memories and returns
the match.

## Memory vs CLAUDE.md

| Use case | Where it belongs |
|----------|-----------------|
| Permanent project rules | CLAUDE.md |
| Session-to-session notes | Memory |
| Architecture decisions | Memory (or CLAUDE.md for critical ones) |
| Temporary working state | Context (session only) |
| Debugging patterns | Memory |

CLAUDE.md is for rules that apply to every session.
Memory is for things you learn along the way.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is code quality?"** for code review tools
- Say **"tell me about security audit"** for vulnerability scanning
