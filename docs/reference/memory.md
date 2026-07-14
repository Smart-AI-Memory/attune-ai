# Memory

## Reference

The recommended surface is `UnifiedMemory` from `attune.memory`. The
security/loader classes (`Classification`, `PIIScrubber`,
`SecretsDetector`, `AuditLogger`, `ClaudeMemoryLoader`,
`MemoryControlPanel`) are re-exported from `attune.memory` too; the
backend **protocols** live in `attune.memory.backend` (they are not
re-exported from the package root).

### `UnifiedMemory` — `attune.memory`

| Symbol | Purpose |
|--------|---------|
| `UnifiedMemory(user_id, config=MemoryConfig.from_environment(), access_tier=AccessTier.CONTRIBUTOR)` | Construct the unified memory. `user_id` is required. |
| `stash(key, value, ttl_seconds=None) -> bool` | Write short-term working memory. |
| `retrieve(key) -> Any \| None` | Read short-term memory; `None` if missing/expired. |
| `persist_pattern(content, pattern_type, classification=None, auto_classify=True, metadata=None) -> dict \| None` | Store a durable pattern (classified + scrubbed first). |
| `recall_pattern(pattern_id, check_permissions=True, use_cache=True) -> dict \| None` | Read a durable pattern by id. |
| `search_patterns(query=None, pattern_type=None, classification=None, limit=10) -> list[dict]` | Query durable patterns by content/type/classification. |
| `stage_pattern(pattern_data, pattern_type="general", ttl_hours=24) -> str \| None` | Stage a candidate pattern; returns a staged id. |
| `promote_pattern(staged_pattern_id, classification=None, auto_classify=True) -> dict \| None` | Promote a staged pattern to durable storage. |
| `get_staged_patterns() -> list[dict]` | List pending staged patterns. |
| `get_capabilities() -> dict[str, bool]` | Backend capability flags. |
| `supports_realtime() / supports_distributed() / supports_persistence() -> bool` | Individual capability checks. |
| `health_check() -> dict` / `get_backend_status() -> dict` | Runtime state. |
| `set_handoff(situation, background, assessment, recommendation, **extra)` | Record an SBAR handoff. |
| `generate_compact_state() -> str` / `export_to_claude_md(path=None) -> Path` | Snapshot state; write it to a CLAUDE.md-style file. |
| `clear_pattern_cache() -> int` / `save() -> None` / `close() -> None` | Cache and lifecycle management. |

### `MemoryConfig` — selected fields

| Field | Default | Meaning |
|-------|---------|---------|
| `environment` | `Environment.DEVELOPMENT` | `development` / `staging` / `production`. |
| `redis_url` / `redis_host` / `redis_port` | `None` / `localhost` / `6379` | Short-term backend coordinates. |
| `redis_mock` / `redis_auto_start` / `redis_required` | `False` / — / — | In-process mock, auto-start, or require Redis. |
| `default_ttl_seconds` | — | Default short-term expiry. |
| `storage_dir` | — | Long-term pattern storage directory. |
| `encryption_enabled` | — | Encrypt `SENSITIVE` patterns at rest. |
| `load_enterprise_memory` / `load_user_memory` / `load_project_memory` | — | Which `CLAUDE.md` levels `ClaudeMemoryLoader` loads. |

Build one from the environment with `MemoryConfig.from_environment()`.

### Backend protocols — `attune.memory.backend`

| Protocol | Methods |
|----------|---------|
| `MemoryBackend` | `stash(key, value, ttl, agent_id)`, `retrieve(key, agent_id)`, `delete(key)`, `keys(pattern)`, `is_connected()`, `get_stats()`, `close()`, `supports_realtime()`, `supports_distributed()`. |
| `SearchableMemoryBackend` | Extends `MemoryBackend` with `search(query, limit)`, `remember(content, ...)`, `promote(session_id)`, `prune(max_age_days)`, `recent(limit)`. |

Both are `@runtime_checkable` — any class implementing the methods
satisfies the protocol.

### Security and loader surface — `attune.memory`

| Symbol | Role |
|--------|------|
| `Classification` | `PUBLIC` / `INTERNAL` / `SENSITIVE`. |
| `PIIScrubber` | Strips personally identifiable information before storage. |
| `SecretsDetector` | Flags credential-like content. |
| `AuditLogger` | Records writes/reads as `AuditEvent`s for compliance. |
| `ClaudeMemoryLoader` | Resolves + merges `CLAUDE.md` levels; entry point `load_all_memory()`. |
| `MemoryControlPanel` | Runtime management — browse, export, and clear stored memory. |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python (recommended) | `from attune.memory import UnifiedMemory`. |
| Custom backend | Implement `MemoryBackend` / `SearchableMemoryBackend` (from `attune.memory.backend`). |
| Static context | `ClaudeMemoryLoader().load_all_memory()`. |
| Runtime management | `MemoryControlPanel`. |

<!-- attune-generated: source_hash=cba94c001e0b9e2f41279e9caa28b69cdc1ff0b0c62ec76baa038dc0e48cb5b6 feature=memory kind=reference generated_at=2026-07-14 -->
