---
feature: memory
depth: concept
generated_at: 2026-04-13T16:57:39.724217+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory

## How it works

Memory subsystem provides storage, retrieval, and enterprise-grade security for AI interactions.

The main building blocks are:

- **`MemoryBackend`** — Protocol for short-term memory backends that store conversation context.
- **`SearchableMemoryBackend`** — Extended protocol for backends with semantic search capabilities.
- **`ClaudeMemoryConfig`** — Configuration for integrating Claude's memory system with your projects.
- **`MemoryFile`** — Represents a loaded CLAUDE.md memory file containing project context.
- **`ClaudeMemoryLoader`** — Loads and manages Claude Code memory files from your project directories.

Under the hood, this feature spans 72 source
files covering:

- Memory backend protocols for Attune AI short-term storage
- Claude memory integration for project-specific context
- Redis configuration utilities (deprecated)
- Enterprise control panel for memory management
- Rate limiting and API key authentication

## What connects to it

This feature relates to: memory, storage.

Other parts of the codebase interact with
memory through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryBackend` | Protocol for short-term memory backends that store conversation context. | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search capabilities. | `src/attune/memory/backend.py` |
| `ClaudeMemoryConfig` | Configuration for integrating Claude's memory system with your projects. | `src/attune/memory/claude_memory.py` |
| `MemoryFile` | Represents a loaded CLAUDE.md memory file containing project context. | `src/attune/memory/claude_memory.py` |
| `ClaudeMemoryLoader` | Loads and manages Claude Code memory files from your project directories. | `src/attune/memory/claude_memory.py` |
