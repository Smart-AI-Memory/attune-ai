---
type: faq
feature: memory
depth: faq
generated_at: 2026-04-14T15:06:37.509869+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory FAQ

## What is the memory feature?

The memory feature provides storage, retrieval, and security for AI agent data. It includes short-term memory backends (like Redis), Claude memory file integration, and enterprise-level security controls.

## When should I use memory?

Use memory when you need to:
- Store and retrieve data between AI conversations
- Load Claude memory files (CLAUDE.md) for context
- Manage agent memory across sessions
- Implement memory security and audit controls

## What are the main classes I should know about?

Start with these core classes:

- `MemoryBackend` — Protocol for implementing short-term memory storage
- `ClaudeMemoryLoader` — Loads CLAUDE.md files for AI context
- `MemoryControlPanel` — Enterprise management for memory operations

## How do I set up Redis memory?

Use `get_redis_memory()` to create a Redis backend with environment-based configuration. For Railway deployment, use `get_railway_redis()` which handles the REDIS_URL automatically.

## How do I load Claude memory files?

Create a `ClaudeMemoryLoader` and call `load_all_memory()`:

```python
loader = ClaudeMemoryLoader()
memory_content = loader.load_all_memory(project_root="/path/to/project")
```

## Can I check if Redis is available without connecting?

Yes, use `is_redis_available()` to check if the Redis subsystem is available without importing it or establishing a connection.

## How do I debug memory issues?

Run the memory tests first: `pytest -k "memory" -v`. If they pass but your code fails, check the Redis connection with `check_redis_connection()` and enable debug logging to trace memory operations.

## Where are the source files?

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
