---
type: note
feature: memory
depth: note
generated_at: 2026-04-14T15:07:06.554871+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Note: memory

## Context

The memory subsystem provides storage, retrieval, and security capabilities for Attune AI. It supports both short-term caching and long-term pattern storage with enterprise-grade security features.

## Architecture

The memory system operates on two levels:

**Protocol layer** — `MemoryBackend` and `SearchableMemoryBackend` define interfaces for storage implementations. The base protocol handles key-value operations with TTL support, while the searchable extension adds semantic search capabilities.

**Implementation layer** — Redis provides the primary backend through `RedisShortTermMemory`, with file-based fallbacks for development environments.

## Claude integration

The `ClaudeMemoryLoader` manages CLAUDE.md files that contain project context and coding patterns. These files can be organized hierarchically:

- Enterprise level (`/enterprise/CLAUDE.md`)
- Project level (`/project/CLAUDE.md`)
- User level (`.claude/CLAUDE.md`)

The loader respects import dependencies and validates file sizes to prevent memory exhaustion during large project scans.

## Enterprise features

The `MemoryControlPanel` provides administrative controls for production deployments:

- Pattern classification (healthcare, financial, proprietary)
- Access control with audit logging
- PII detection and scrubbing
- Cross-session coordination for multi-agent environments

Redis configuration supports Railway deployment through `get_railway_redis()`, which requires the `REDIS_URL` environment variable from Railway's database add-ons.

## Security model

Memory operations enforce classification rules based on content analysis. Sensitive patterns (clinical protocols, financial procedures) require elevated access tiers. The `EncryptionManager` handles encryption-at-rest when the cryptography library is available.
