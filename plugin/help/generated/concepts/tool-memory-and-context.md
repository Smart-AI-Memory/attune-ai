---
type: concept
name: tool-memory-and-context
tags: [memory, context, persistence]
source: plugin/skills/memory-and-context/SKILL.md
---

# Memory and Context

## What

Provides persistent cross-session storage for patterns,
decisions, and project context. Stores key-value memories
with tags and timestamps, supports search and recall, and
manages attune levels (1-5) that control how much
contextual adaptation the system applies.

## Why

Every new Claude Code session starts with a blank slate.
Memory bridges that gap -- storing what worked, what
failed, and what the project conventions are so the next
session picks up where the last one left off.

## When to use

- To save a debugging pattern you want to remember
- To store project conventions (naming, architecture)
- To adjust attune level for more or less adaptation
- To recall context from a previous session

## What it covers

| Feature | Description |
|---------|-------------|
| Store | Save key-value pairs with tags |
| Recall | Retrieve by key or search by tag |
| Search | Full-text search across all memories |
| Attune levels | 1 (minimal) to 5 (full adaptation) |
| Security | Classified pattern storage with access control |

## Related Topics

- **Task**: Use the memory-and-context skill -- step-by-step
- **Reference**: Skill: memory-and-context -- full reference
