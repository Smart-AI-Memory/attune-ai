---
feature: memory
depth: concept
generated_at: 2026-04-04T02:25:50.438058+00:00
source_hash: f7be50272674d976f7e23f12d2da9909620b48df295f03bbf3d21d0e9e8b1034
status: generated
---

# Memory

## What

Memory subsystem — storage, retrieval, and security

## Why

This feature provides memory functionality for the project.

## How

Key components:

- `MemoryBackend` — Protocol for short-term memory backends.

- `SearchableMemoryBackend` — Extended protocol for backends with semantic search.

- `ClaudeMemoryConfig` — Configuration for Claude memory integration

- `MemoryFile` — Represents a loaded CLAUDE.md memory file

- `ClaudeMemoryLoader` — Loads and manages Claude Code memory files (CLAUDE.md).
