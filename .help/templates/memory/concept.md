---
feature: memory
depth: concept
generated_at: 2026-06-03T12:45:43.107743+00:00
source_hash: aef54dd763ecee5292afdaa47a99e48e4d68ab66ba2bedf0a15d83d09ad51782
status: generated
---

# Memory

## How it works

Memory subsystem — storage, lookup, and security.

The main building blocks are:

- **`MemoryBackend`** — Protocol for short-term memory backends.
- **`SearchableMemoryBackend`** — Extended protocol for backends with semantic search.
- **`ClaudeMemoryConfig`** — Configuration for Claude memory integration
- **`MemoryFile`** — Represents a loaded CLAUDE.md memory file
- **`ClaudeMemoryLoader`** — Loads and manages Claude Code memory files (CLAUDE.md).

Under the hood, this feature spans 74 source
files covering:

- Memory backend protocol for Attune AI.
- Claude Memory Integration Module
- Redis Configuration for Attune AI (deprecated).

## What connects to it

This feature relates to: memory, storage.

Other parts of the codebase interact with
memory through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryBackend` | Protocol for short-term memory backends. | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search. | `src/attune/memory/backend.py` |
| `ClaudeMemoryConfig` | Configuration for Claude memory integration | `src/attune/memory/claude_memory.py` |
| `MemoryFile` | Represents a loaded CLAUDE.md memory file | `src/attune/memory/claude_memory.py` |
| `ClaudeMemoryLoader` | Loads and manages Claude Code memory files (CLAUDE.md). | `src/attune/memory/claude_memory.py` |
