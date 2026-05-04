---
type: concept
feature: memory
depth: concept
generated_at: 2026-05-04T02:31:38.489537+00:00
source_hash: c45e8890bff96a3bad01adc0d5e2914aa9058b01f5de4c8a1985c9b6fe4a7f0f
status: generated
---

# Memory

Memory is Attune AI's system for storing, retrieving, and securing conversational context and learned patterns across agent sessions.

## Storage architecture

Memory operates on three layers:

**Short-term storage** handles session data through the `MemoryBackend` protocol. Backends like Redis store key-value pairs with TTL (time-to-live) expiration, agent-scoped namespacing, and connection pooling. The `SearchableMemoryBackend` extends this with semantic search capabilities for finding related context.

**Claude integration** loads project-specific memory files through `ClaudeMemoryLoader`. It scans for `CLAUDE.md` files at enterprise, project, and user levels, respects import hierarchies, and validates file sizes. The `ClaudeMemoryConfig` controls which memory levels to load and sets safety limits.

**Long-term storage** uses the `MemDocsStorage` system with encryption, classification rules, and audit trails. Patterns are tagged as healthcare, financial, or proprietary based on content analysis, then access-controlled per user permissions.

## Security model

Memory implements defense in depth:

- **Classification** — Automatic tagging of sensitive content (healthcare keywords trigger HIPAA handling, financial terms enable PCI compliance)
- **Encryption** — At-rest encryption for classified patterns with key rotation
- **Access control** — Role-based permissions checked before retrieval
- **Audit logging** — Complete trails of pattern access and modifications
- **PII scrubbing** — Detection and masking of personal identifiers
- **Secret detection** — Prevention of API keys and credentials from being stored

## Cross-session coordination

The `CrossSessionCoordinator` handles conflicts when multiple agents access shared memory. It uses Redis pub/sub channels to broadcast session changes, implements optimistic locking for pattern updates, and provides conflict resolution strategies (merge, override, or user prompt).

## Control and monitoring

The `MemoryControlPanel` provides operational visibility:

- Real-time statistics on storage usage and hit rates
- Pattern management (list, delete, export by classification)
- Redis health monitoring and auto-restart capabilities
- Rate limiting and API key authentication for remote access
- HTTP API server for web-based administration

Memory backends expose standardized metrics through `get_stats()` including connection status, key counts, memory usage, and operation latencies.
