---
type: comparison
feature: memory
depth: comparison
generated_at: 2026-04-14T15:07:17.959773+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory backend options for Attune AI

## Overview

Attune AI supports multiple memory backends for different storage and retrieval patterns. This comparison helps you choose between short-term caching, long-term pattern storage, and file-based memory systems.

## Memory backend comparison

| Feature | Redis (short-term) | MemDocs (long-term) | Claude Memory (file-based) | Control Panel |
|---------|-------------------|---------------------|---------------------------|---------------|
| **Primary use case** | Session caching, temporary storage | Pattern storage, semantic search | Project context, documentation | Enterprise management |
| **Persistence** | TTL-based expiration | Permanent until deleted | File system persistence | Administrative oversight |
| **Search capability** | Key pattern matching | Full semantic search | Import-based loading | Pattern classification |
| **Distribution** | Multi-agent support via pub/sub | Centralized storage | Local file system | Cross-system coordination |
| **Performance** | ~1ms retrieval for cached data | Optimized for complex queries | File I/O dependent | Management operations |
| **Security** | Basic key isolation | PII scrubbing, encryption | File system permissions | Audit logging, access control |

## Storage strategies

### Redis short-term memory
Best for session state and temporary caching. Supports agent isolation and cross-session coordination through pub/sub channels.

```python
# Fast retrieval with TTL
backend.stash("session_context", data, ttl=3600, agent_id="agent_123")
result = backend.retrieve("session_context", agent_id="agent_123")
```

### MemDocs long-term storage
Handles persistent patterns with semantic search. Includes built-in security features like PII detection and classification.

```python
# Semantic search across stored patterns
results = backend.search("debugging workflow", limit=5)
backend.promote(session_id="current_session")  # Move to long-term
```

### Claude Memory files
Project-specific context loaded from CLAUDE.md files with import resolution and validation.

```python
# Load hierarchical project memory
loader = ClaudeMemoryLoader(config)
context = loader.load_all_memory(project_root="/path/to/project")
```

## Use Redis when you need:

- **Session state management** — User interactions, temporary calculations, or workflow state that expires naturally
- **Cross-agent coordination** — Multiple agents sharing data through pub/sub channels
- **High-frequency operations** — Sub-millisecond retrieval for frequently accessed data
- **Railway deployment** — Built-in Railway Redis integration with `get_railway_redis()`

## Use MemDocs when you need:

- **Semantic search** — Finding patterns by meaning rather than exact key matches
- **Long-term pattern storage** — Debugging workflows, architectural decisions, or learned behaviors
- **Enterprise security** — PII scrubbing, access classification, and audit trails
- **Pattern promotion** — Moving useful session data to permanent storage

## Use Claude Memory when you need:

- **Project context** — Loading documentation and guidelines specific to a codebase
- **Hierarchical imports** — CLAUDE.md files that reference other memory files
- **File-based persistence** — Version-controlled memory that lives alongside your code
- **Static context loading** — Pre-defined knowledge that doesn't change during execution

## Use Control Panel when you need:

- **Enterprise management** — Administrative oversight of memory systems across teams
- **Pattern governance** — Classifying and controlling access to sensitive patterns
- **System monitoring** — Health checks, statistics, and performance tracking
- **Audit compliance** — Logging and reporting for regulatory requirements

The Control Panel orchestrates other memory backends rather than storing data directly — choose it when you need administrative control over existing memory systems.
