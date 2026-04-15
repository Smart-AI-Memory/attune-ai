---
type: concept
feature: memory
depth: concept
generated_at: 2026-04-14T15:04:29.013517+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory

## How it works

Memory is Attune AI's unified system for storing and retrieving agent knowledge, from temporary session data to persistent project context.

The system operates through pluggable backends that can store data with TTL-based expiration, semantic search capabilities, and Redis-based distributed access. You can stash key-value pairs for quick retrieval, promote session memories to long-term storage, and load structured project knowledge from CLAUDE.md files.

## Core components

- **Short-term backends** — `MemoryBackend` protocol defines basic storage operations like `stash()`, `retrieve()`, and `delete()` with optional TTL expiration
- **Searchable backends** — `SearchableMemoryBackend` extends basic storage with semantic `search()` queries and session `promote()` capabilities
- **Claude integration** — `ClaudeMemoryLoader` discovers and loads CLAUDE.md files from project hierarchies, respecting import dependencies and file size limits
- **Control panel** — `MemoryControlPanel` provides enterprise-grade management with Redis orchestration, pattern export, and health monitoring
- **Security layer** — Built-in PII scrubbing, secret detection, and classification rules protect sensitive data

## Memory lifecycle

When you stash data, the backend stores it with an optional TTL and agent-specific scoping. For searchable backends, you can later promote valuable session data to permanent storage or query it semantically. The Claude memory loader scans project directories for CLAUDE.md files, following import chains up to a configurable depth while validating file sizes and formats.

## What connects to it

Other parts of the codebase interact with memory through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryBackend` | Basic storage with TTL and agent scoping | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Semantic search and session promotion | `src/attune/memory/backend.py` |
| `ClaudeMemoryLoader` | Project knowledge from CLAUDE.md files | `src/attune/memory/claude_memory.py` |
| `MemoryControlPanel` | Enterprise management and Redis control | `src/attune/memory/control_panel.py` |
| `SecureMemDocsIntegration` | Security-aware long-term storage | `src/attune/memory/secure.py` |
