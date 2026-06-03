---
feature: memory
depth: concept
generated_at: 2026-06-03T16:28:50.316906+00:00
source_hash: a5579e8907712bf584f1ae5f2c1991e29aa4fdc4f749495b823c67f323543a57
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

Under the hood, this feature spans 75 source
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
