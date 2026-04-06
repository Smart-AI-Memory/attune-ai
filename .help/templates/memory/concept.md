---
feature: memory
depth: concept
generated_at: 2026-04-06T04:31:02.171580+00:00
source_hash: f7be50272674d976f7e23f12d2da9909620b48df295f03bbf3d21d0e9e8b1034
status: generated
---

# Memory

## How it works

Memory subsystem provides persistent storage, semantic search, and centralized management for AI interactions.

The main building blocks are:

- **`MemoryBackend`** — Protocol that defines the interface for short-term memory storage systems.
- **`SearchableMemoryBackend`** — Extended protocol that adds semantic search capabilities to memory backends.
- **`ClaudeMemoryConfig`** — Configuration settings for integrating with Claude's memory system.
- **`MemoryFile`** — Represents a loaded CLAUDE.md file containing project-specific memory data.
- **`ClaudeMemoryLoader`** — Manages loading and parsing of CLAUDE.md memory files for code projects.

Under the hood, this feature spans 145 source
files covering:

- Memory backend protocols and implementations
- Claude memory integration for code projects
- Enterprise control panel for memory management
- Redis-based storage (legacy support)

## What connects to it

This feature relates to: memory, storage.

Other parts of the codebase interact with
memory through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryBackend` | Protocol that defines the interface for short-term memory storage systems. | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Extended protocol that adds semantic search capabilities to memory backends. | `src/attune/memory/backend.py` |
| `ClaudeMemoryConfig` | Configuration settings for integrating with Claude's memory system. | `src/attune/memory/claude_memory.py` |
| `MemoryFile` | Represents a loaded CLAUDE.md file containing project-specific memory data. | `src/attune/memory/claude_memory.py` |
| `ClaudeMemoryLoader` | Manages loading and parsing of CLAUDE.md memory files for code projects. | `src/attune/memory/claude_memory.py` |
