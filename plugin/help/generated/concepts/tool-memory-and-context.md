---
name: tool-memory-and-context
source: plugin/skills/memory-and-context/SKILL.md
summary: Memory and Context provides persistent, cross-session storage for project
  patterns, decisions, and conventions through tagged key-value pairs with searchable
  recall and adjustable attune levels (1–5) that control contextual adaptation.
tags:
- memory
- context
- persistence
type: concept
---

# Memory and Context

## Overview

Memory and Context provides persistent, cross-session storage for patterns, decisions, and project context. It stores key-value memories with tags and timestamps, supports search and recall, and manages attune levels (1–5) that control how much contextual adaptation the system applies.

## Why It Matters

Every new Claude Code session starts with a blank slate. Memory bridges that gap — storing what worked, what failed, and what your project conventions are, so each new session picks up where the last one left off.

## When to Use

- Save a debugging pattern you want to reuse later
- Store project conventions such as naming standards or architectural decisions
- Adjust the attune level to increase or decrease contextual adaptation
- Recall context established in a previous session

## Features

| Feature | Description |
|---|---|
| Store | Save key-value pairs with optional tags |
| Recall | Retrieve memories by key or filter by tag |
| Search | Full-text search across all stored memories |
| Attune levels | Scale from 1 (minimal adaptation) to 5 (full adaptation) |
| Security | Classified pattern storage with access control |

## Related Topics

- **Task** — Memory and Context: step-by-step usage guide
- **Reference** — Memory and Context: complete skill reference
