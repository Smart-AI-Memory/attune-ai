# Stage 1 Analysis: memory/short_term.py

**Created:** 2026-02-02
**Status:** Phase 2 Complete - Structure Created
**File:** `src/attune/memory/short_term.py` (2,198 lines)

---

## Progress Tracker

| Phase | Status | Description |
| ----- | ------ | ----------- |
| Phase 1 | COMPLETE | Analysis - method mapping, dependencies, test coverage |
| Phase 2 | COMPLETE | Directory structure created with 17 module files |
| Phase 3 | PENDING | Extract base.py - core CRUD operations |
| Phase 4 | PENDING | Extract caching.py, security.py |
| Phase 5 | PENDING | Extract working.py, patterns.py |
| Phase 6 | PENDING | Extract conflicts.py, sessions.py |
| Phase 7 | PENDING | Extract batch, pagination, pubsub, streams, timelines, queues, transactions, cross_session |
| Phase 8 | PENDING | Complete facade, verify all imports work |

**Phase 2 Deliverables:**

```text
src/attune/memory/short_term/
├── __init__.py          # Re-exports (placeholder)
├── facade.py            # Composition pattern (placeholder)
├── base.py              # Core CRUD operations (docstring only)
├── caching.py           # Local LRU cache (docstring only)
├── security.py          # PII/secrets (docstring only)
├── working.py           # Stash/retrieve (docstring only)
├── patterns.py          # Pattern staging (docstring only)
├── conflicts.py         # Conflict negotiation (docstring only)
├── sessions.py          # Session management (docstring only)
├── batch.py             # Batch operations (docstring only)
├── pagination.py        # SCAN pagination (docstring only)
├── pubsub.py            # Pub/Sub (docstring only)
├── streams.py           # Redis Streams (docstring only)
├── timelines.py         # Time queries (docstring only)
├── queues.py            # Task queues (docstring only)
├── transactions.py      # Atomic ops (docstring only)
└── cross_session.py     # Cross-session (docstring only)
```

---

## Executive Summary

The `RedisShortTermMemory` class is a god class with 50+ methods covering 8 distinct concerns. This analysis maps each method to its target module for the refactoring.

---

## Method-to-Module Mapping

### 1. base.py - Core CRUD Operations (Target: ~200 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `__init__` | 118-215 | Constructor | All shared state |
| `client` (property) | 216-228 | Redis client getter | `_client` |
| `metrics` (property) | 230-241 | Metrics getter | `_metrics` |
| `_create_client_with_retry` | 243-284 | Connection with retry | `_config`, `_metrics` |
| `_execute_with_retry` | 286-317 | Operation retry wrapper | `_config`, `_metrics` |
| `_get` | 319-359 | Get value (with cache) | `_client`, `_mock_storage`, `_local_cache*` |
| `_set` | 361-390 | Set value (with cache) | `_client`, `_mock_storage`, `_local_cache*` |
| `_delete` | 392-418 | Delete key | `_client`, `_mock_storage`, `_local_cache` |
| `_keys` | 420-431 | Get keys by pattern | `_client`, `_mock_storage` |
| `ping` | 1075-1089 | Health check | `_client`, `use_mock` |
| `get_stats` | 1091-1125 | Memory statistics | `_client`, `_mock_storage` |
| `get_metrics` | 1127-1134 | Operation metrics | `_metrics` |
| `reset_metrics` | 1136-1138 | Reset metrics | `_metrics` |
| `close` | 2191-2197 | Cleanup | `_client`, `close_pubsub` |

### 2. caching.py - Local LRU Cache Layer (Target: ~80 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `_add_to_local_cache` | 435-451 | Add entry with LRU eviction | `_local_cache*` state |
| `clear_local_cache` | 453-464 | Clear all cache | `_local_cache*` state |
| `get_local_cache_stats` | 466-483 | Cache performance stats | `_local_cache*` state |

**Shared State:**
- `_local_cache_enabled: bool`
- `_local_cache_max_size: int`
- `_local_cache: dict[str, tuple[str, float, float]]`
- `_local_cache_hits: int`
- `_local_cache_misses: int`

### 3. security.py - Data Sanitization (Target: ~100 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `_sanitize_data` | 487-570 | PII scrubbing + secrets detection | `_pii_scrubber`, `_secrets_detector`, `_metrics` |

**Shared State:**
- `_pii_scrubber: PIIScrubber | None`
- `_secrets_detector: SecretsDetector | None`

### 4. working.py - Working Memory (Stash/Retrieve) (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `stash` | 574-635 | Store data | `_sanitize_data`, `_set`, `PREFIX_WORKING` |
| `retrieve` | 637-672 | Get data | `_get`, `PREFIX_WORKING` |
| `clear_working_memory` | 674-690 | Clear agent's memory | `_keys`, `_delete`, `PREFIX_WORKING` |

### 5. patterns.py - Pattern Staging (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `stage_pattern` | 694-731 | Stage pattern for validation | `_set`, `PREFIX_STAGED` |
| `get_staged_pattern` | 733-761 | Retrieve staged pattern | `_get`, `PREFIX_STAGED` |
| `list_staged_patterns` | 763-785 | List all staged | `_keys`, `_get`, `PREFIX_STAGED` |
| `promote_pattern` | 787-812 | Promote to library | `get_staged_pattern`, `_delete` |
| `reject_pattern` | 814-838 | Reject pattern | `_delete`, `PREFIX_STAGED` |

### 6. conflicts.py - Conflict Negotiation (Target: ~120 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `create_conflict_context` | 842-902 | Create negotiation context | `_set`, `PREFIX_CONFLICT` |
| `get_conflict_context` | 904-932 | Retrieve conflict | `_get`, `PREFIX_CONFLICT` |
| `resolve_conflict` | 934-967 | Mark resolved | `get_conflict_context`, `_set` |

### 7. sessions.py - Session Management (Target: ~100 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `create_session` | 976-1013 | Create collaboration session | `_set`, `PREFIX_SESSION` |
| `join_session` | 1015-1047 | Join existing session | `_get`, `_set`, `PREFIX_SESSION` |
| `get_session` | 1049-1071 | Get session info | `_get`, `PREFIX_SESSION` |

### 8. batch.py - Batch Operations (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `stash_batch` | 1144-1221 | Batch stash | `_client`, `_mock_storage`, `_metrics`, `PREFIX_WORKING` |
| `retrieve_batch` | 1223-1276 | Batch retrieve | `_client`, `_mock_storage`, `_metrics`, `PREFIX_WORKING` |

### 9. pagination.py - SCAN-based Pagination (Target: ~100 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `list_staged_patterns_paginated` | 1282-1360 | Paginated pattern list | `_client`, `_mock_storage`, `_metrics`, `PREFIX_STAGED` |
| `scan_keys` | 1362-1398 | Generic key scanning | `_client`, `_mock_storage` |

### 10. pubsub.py - Pub/Sub Messaging (Target: ~180 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `publish` | 1404-1458 | Publish message | `_client`, `_mock_pubsub_handlers`, `_metrics`, `PREFIX_PUBSUB` |
| `subscribe` | 1460-1517 | Subscribe to channel | `_client`, `_pubsub*`, `_subscriptions`, `PREFIX_PUBSUB` |
| `_pubsub_message_handler` | 1519-1538 | Internal handler | `_subscriptions` |
| `_pubsub_listener` | 1540-1547 | Background listener | `_pubsub*` |
| `unsubscribe` | 1549-1570 | Unsubscribe | `_pubsub`, `_mock_pubsub_handlers`, `_subscriptions` |
| `close_pubsub` | 1572-1578 | Close pubsub | `_pubsub*`, `_subscriptions` |

**Shared State:**
- `_pubsub: Any | None`
- `_pubsub_thread: threading.Thread | None`
- `_subscriptions: dict[str, list[Callable]]`
- `_pubsub_running: bool`
- `_mock_pubsub_handlers: dict`

### 11. streams.py - Redis Streams (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `stream_append` | 1584-1648 | Append to stream | `_client`, `_mock_streams`, `_metrics`, `PREFIX_STREAM` |
| `stream_read` | 1650-1688 | Read from stream | `_client`, `_mock_streams`, `PREFIX_STREAM` |
| `stream_read_new` | 1690-1726 | Read new entries (blocking) | `_client`, `PREFIX_STREAM` |

**Shared State:**
- `_mock_streams: dict[str, list[tuple[str, dict]]]`

### 12. timelines.py - Time-Window Queries (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `timeline_add` | 1732-1783 | Add to timeline | `_client`, `_mock_sorted_sets`, `PREFIX_TIMELINE` |
| `timeline_query` | 1785-1836 | Query time window | `_client`, `_mock_sorted_sets`, `PREFIX_TIMELINE` |
| `timeline_count` | 1838-1867 | Count in window | `_client`, `_mock_sorted_sets`, `PREFIX_TIMELINE` |

**Shared State:**
- `_mock_sorted_sets: dict[str, list[tuple[float, str]]]`

### 13. queues.py - Task Queues (Target: ~150 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `queue_push` | 1873-1925 | Push task | `_client`, `_mock_lists`, `PREFIX_QUEUE` |
| `queue_pop` | 1927-1972 | Pop task | `_client`, `_mock_lists`, `PREFIX_QUEUE` |
| `queue_length` | 1974-1992 | Queue length | `_client`, `_mock_lists`, `PREFIX_QUEUE` |
| `queue_peek` | 1994-2021 | Peek without removing | `_client`, `_mock_lists`, `PREFIX_QUEUE` |

**Shared State:**
- `_mock_lists: dict[str, list[str]]`

### 14. transactions.py - Atomic Operations (Target: ~100 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `atomic_promote_pattern` | 2027-2128 | Atomic pattern promotion | `_client`, `_mock_storage`, `_local_cache`, `PREFIX_STAGED` |

### 15. cross_session.py - Cross-Session Coordination (Target: ~60 lines)

| Method | Lines | Description | Dependencies |
|--------|-------|-------------|--------------|
| `enable_cross_session` | 2134-2176 | Enable cross-session | `use_mock`, imports `CrossSessionCoordinator` |
| `cross_session_available` | 2178-2185 | Check availability | `use_mock`, `_client` |

---

## Shared State Analysis

### Core State (Required by all modules)

```python
# In base.py - shared across all modules
class SharedState:
    _config: RedisConfig
    _client: redis.Redis | None
    _metrics: RedisMetrics
    use_mock: bool
```

### Mock Storage (Required when use_mock=True)

```python
# In base.py or mock.py
class MockStorage:
    _mock_storage: dict[str, tuple[Any, float | None]]  # key -> (value, expires)
    _mock_lists: dict[str, list[str]]                    # queue operations
    _mock_sorted_sets: dict[str, list[tuple[float, str]]]  # timelines
    _mock_streams: dict[str, list[tuple[str, dict]]]     # streams
    _mock_pubsub_handlers: dict[str, list[Callable]]     # pubsub
```

### Local Cache State

```python
# In caching.py
class LocalCacheState:
    _local_cache_enabled: bool
    _local_cache_max_size: int
    _local_cache: dict[str, tuple[str, float, float]]
    _local_cache_hits: int
    _local_cache_misses: int
```

### Pub/Sub State

```python
# In pubsub.py
class PubSubState:
    _pubsub: Any | None
    _pubsub_thread: threading.Thread | None
    _subscriptions: dict[str, list[Callable[[dict], None]]]
    _pubsub_running: bool
```

### Security State

```python
# In security.py (or base.py)
class SecurityState:
    _pii_scrubber: PIIScrubber | None
    _secrets_detector: SecretsDetector | None
```

---

## Key Prefixes

All modules need access to these constants:

```python
PREFIX_WORKING = "empathy:working:"
PREFIX_STAGED = "empathy:staged:"
PREFIX_CONFLICT = "empathy:conflict:"
PREFIX_SESSION = "empathy:session:"
PREFIX_PUBSUB = "empathy:pubsub:"
PREFIX_STREAM = "empathy:stream:"
PREFIX_TIMELINE = "empathy:timeline:"
PREFIX_QUEUE = "empathy:queue:"
```

---

## Public API (Must Remain Backward Compatible)

### Primary API (Documented in docstrings)

```python
# Working Memory
stash(key, data, credentials, ttl, skip_sanitization) -> bool
retrieve(key, credentials, agent_id) -> Any | None
clear_working_memory(credentials) -> int

# Pattern Staging
stage_pattern(pattern, credentials) -> bool
get_staged_pattern(pattern_id, credentials) -> StagedPattern | None
list_staged_patterns(credentials) -> list[StagedPattern]
promote_pattern(pattern_id, credentials) -> StagedPattern | None
reject_pattern(pattern_id, credentials, reason) -> bool

# Conflict Negotiation
create_conflict_context(conflict_id, positions, interests, credentials, batna) -> ConflictContext
get_conflict_context(conflict_id, credentials) -> ConflictContext | None
resolve_conflict(conflict_id, resolution, credentials) -> bool

# Session Management
create_session(session_id, credentials, metadata) -> bool
join_session(session_id, credentials) -> bool
get_session(session_id, credentials) -> dict | None

# Batch Operations
stash_batch(items, credentials, ttl) -> int
retrieve_batch(keys, credentials, agent_id) -> dict[str, Any]

# Pagination
list_staged_patterns_paginated(credentials, cursor, count) -> PaginatedResult
scan_keys(pattern, cursor, count) -> PaginatedResult

# Pub/Sub
publish(channel, message, credentials) -> int
subscribe(channel, handler, credentials) -> bool
unsubscribe(channel) -> bool
close_pubsub() -> None

# Streams
stream_append(stream_name, data, credentials, max_len) -> str | None
stream_read(stream_name, credentials, start_id, count) -> list[tuple]
stream_read_new(stream_name, credentials, block_ms, count) -> list[tuple]

# Timelines
timeline_add(timeline_name, event_id, data, credentials, timestamp) -> bool
timeline_query(timeline_name, credentials, query) -> list[dict]
timeline_count(timeline_name, credentials, query) -> int

# Queues
queue_push(queue_name, task, credentials, priority) -> int
queue_pop(queue_name, credentials, timeout) -> dict | None
queue_length(queue_name) -> int
queue_peek(queue_name, credentials, count) -> list[dict]

# Transactions
atomic_promote_pattern(pattern_id, credentials, min_confidence) -> tuple[bool, StagedPattern | None, str]

# Cross-Session
enable_cross_session(access_tier, auto_announce) -> CrossSessionCoordinator
cross_session_available() -> bool

# Lifecycle
ping() -> bool
get_stats() -> dict
get_metrics() -> dict
reset_metrics() -> None
close() -> None

# Properties
client -> Any
metrics -> RedisMetrics
```

### Import Sites to Verify (21 source files + tests)

**Source Files (Must Maintain Backward Compatibility):**

| File | Lines | Import Type | Action Required |
| ---- | ----- | ----------- | --------------- |
| `src/attune/redis_memory.py` | 161 | Has own `RedisShortTermMemory` copy | Keep as-is (separate implementation) |
| `src/attune/redis_config.py` | 48,59,172-227,282 | Import + factory functions | Verify facade works |
| `src/attune/__init__.py` | 126,211,324 | Re-export | Point to facade |
| `src/attune/dashboard/simple_server.py` | 137-374 | 10 endpoint imports | All use `from attune.memory.short_term import` |
| `src/attune/memory/summary_index.py` | 24,134 | Import + type hint | Verify facade works |
| `src/attune/memory/redis_bootstrap.py` | 528-538 | Import + factory | Verify facade works |
| `src/attune/workflows/autonomous_test_gen.py` | 35,99 | Import + instantiation | Verify facade works |
| `src/attune/memory/cross_session.py` | 34,144,649,816,828 | Import + type hints | Import from facade |
| `src/attune/memory/file_session.py` | 243 | Docstring reference | No code change needed |
| `src/attune/memory/config.py` | 33,95-137,200 | Import + factory functions | Verify facade works |
| `src/attune/memory/control_panel.py` | 58,235,568,572 | Import + instance | Import from facade |
| `src/attune/memory/__init__.py` | 42,126,203 | Re-export | Point to facade |
| `src/attune/memory/unified.py` | 50,171 | Import + type hint | Import from facade |
| `src/attune/core.py` | 22,153,167 | Import from redis_memory | Uses wrapper, no change |
| `src/attune/memory/mixins/backend_init_mixin.py` | 17,29,52,77,99 | Import + type hints | Import from facade |
| `src/attune/coordination.py` | 433,771 | Docstring type hints | No code change needed |
| `src/attune/memory/mixins/short_term_mixin.py` | 21,34 | Import + type hint | Import from facade |
| `src/attune/memory/mixins/capabilities_mixin.py` | 15,23,60,64 | Import + type hint | Import from facade |
| `src/attune/memory/mixins/lifecycle_mixin.py` | 15,25 | Type hints | Import from facade |
| `src/attune/memory/mixins/promotion_mixin.py` | 15,24 | Import + type hint | Import from facade |

**Test Files (Many files - will continue working with facade):**

| Test Directory | File Count | Notes |
| -------------- | ---------- | ----- |
| `tests/` | 6 files | Direct imports |
| `tests/unit/memory/` | 12 files | Comprehensive unit tests |
| `tests/unit/` | 2 files | Fallback + cross-session |
| `tests/behavioral/` | 1 file | Behavioral tests |

**Key Insight:** All imports use `from attune.memory.short_term import RedisShortTermMemory`, so the facade pattern at `src/attune/memory/short_term.py` will maintain full backward compatibility.

**Additional Exports to Maintain:**

- `RedisConfig` - Configuration dataclass
- `StagedPattern` - Pattern dataclass
- `ConflictContext` - Conflict dataclass
- `AgentCredentials` - Credentials dataclass
- `AccessTier` - Enum
- `TTLStrategy` - Enum
- `TimeWindowQuery` - Query dataclass
- `PaginatedResult` - Result dataclass
- `RedisMetrics` - Metrics dataclass

---

## Recommended Module Structure

```
src/attune/memory/short_term/
├── __init__.py          # Re-exports RedisShortTermMemory
├── base.py              # Core CRUD, connection, retry logic (~250 lines)
├── caching.py           # Local LRU cache (~80 lines)
├── security.py          # PII scrubbing, secrets detection (~100 lines)
├── working.py           # Stash/retrieve operations (~150 lines)
├── patterns.py          # Pattern staging workflow (~150 lines)
├── conflicts.py         # Conflict negotiation (~120 lines)
├── sessions.py          # Session management (~100 lines)
├── batch.py             # Batch operations (~150 lines)
├── pagination.py        # SCAN-based pagination (~100 lines)
├── pubsub.py            # Pub/Sub messaging (~180 lines)
├── streams.py           # Redis Streams (~150 lines)
├── timelines.py         # Time-window queries (~150 lines)
├── queues.py            # Task queues (~150 lines)
├── transactions.py      # Atomic operations (~100 lines)
└── cross_session.py     # Cross-session coordination (~60 lines)
```

**Total:** ~1,895 lines (vs. 2,198 original - cleaner organization)

---

## Dependencies Between Modules

```
base.py (core)
    ↑
    ├── caching.py (uses _get/_set hooks)
    ├── security.py (uses _metrics)
    │
    ├── working.py (uses _get, _set, _delete, _keys, _sanitize_data)
    ├── patterns.py (uses _get, _set, _delete, _keys)
    ├── conflicts.py (uses _get, _set)
    ├── sessions.py (uses _get, _set)
    │
    ├── batch.py (uses _client, _mock_storage, _metrics)
    ├── pagination.py (uses _client, _mock_storage, _metrics)
    │
    ├── pubsub.py (uses _client, _mock_pubsub_handlers, _metrics)
    ├── streams.py (uses _client, _mock_streams, _metrics)
    ├── timelines.py (uses _client, _mock_sorted_sets)
    ├── queues.py (uses _client, _mock_lists)
    │
    ├── transactions.py (uses _client, _mock_storage, _local_cache)
    └── cross_session.py (uses use_mock, _client)
```

---

## Risk Assessment

| Module | Risk Level | Reason |
|--------|------------|--------|
| base.py | LOW | Foundation, extract first |
| caching.py | LOW | Self-contained |
| security.py | LOW | Self-contained |
| working.py | MEDIUM | Core API, many callers |
| patterns.py | MEDIUM | Core API, validation workflow |
| conflicts.py | LOW | Less frequently used |
| sessions.py | LOW | Less frequently used |
| batch.py | LOW | Performance optimization |
| pagination.py | LOW | Performance optimization |
| pubsub.py | MEDIUM | Threading, state management |
| streams.py | LOW | Isolated feature |
| timelines.py | LOW | Isolated feature |
| queues.py | LOW | Isolated feature |
| transactions.py | MEDIUM | Atomic operations critical |
| cross_session.py | LOW | External coordinator |

---

## Next Steps

1. **Phase 2:** Create directory structure and empty module files
2. **Phase 3:** Extract base.py (core CRUD) first
3. **Phase 4:** Extract caching.py (low risk)
4. **Phase 5:** Extract patterns.py (medium risk, core workflow)
5. Continue with remaining modules in risk order

---

## Test Coverage Analysis

**Total Tests:** 327 tests across 10 test files

### Test Files by Focus Area

| Test File | Test Count | Coverage Focus |
| --------- | ---------- | -------------- |
| `tests/test_short_term.py` | 65 | Core operations, dataclasses |
| `tests/unit/memory/test_short_term.py` | 35 | CRUD operations |
| `tests/unit/memory/test_short_term_advanced.py` | 49 | Advanced features |
| `tests/unit/memory/test_short_term_atomic.py` | 19 | Atomic transactions |
| `tests/unit/memory/test_short_term_failures.py` | 24 | Error handling |
| `tests/unit/memory/test_short_term_queues.py` | 21 | Queue operations |
| `tests/unit/memory/test_short_term_streams.py` | 16 | Redis Streams |
| `tests/unit/memory/test_short_term_time_window.py` | 14 | Time window queries |
| `tests/unit/memory/test_short_term_timeline.py` | 20 | Timeline operations |
| `tests/behavioral/` | 64 | Behavioral tests |

### Test Classes Mapped to Target Modules

| Target Module | Test Classes |
| ------------- | ------------ |
| base.py | `TestRedisShortTermMemory*`, `TestRedisConfig`, `TestRedisMetrics`, `TestConnectionRetry`, `TestMetrics` |
| working.py | `TestBasicStashRetrieve`, `TestStash`, `TestRetrieve`, `TestDelete`, `TestAgentWorkingMemory` |
| patterns.py | `TestPatternStaging`, `TestStagedPattern*`, `TestRedisShortTermMemoryPatterns` |
| conflicts.py | `TestConflictContext`, `TestRedisShortTermMemoryConflicts` |
| sessions.py | (integrated into behavioral tests) |
| batch.py | `TestBatchOperations` |
| pagination.py | `TestPagination`, `TestPaginatedOperations`, `TestPaginatedResult` |
| pubsub.py | `TestPubSub`, `TestPubSubOperations` |
| streams.py | `TestRedisStreams`, `TestStreamOperations` |
| timelines.py | `TestTimeline`, `TestTimelineOperations`, `TestTimeWindow*` |
| queues.py | `TestQueueOperations`, `TestTaskQueue*` |
| transactions.py | `TestAtomicOperations`, `TestTransactions`, `TestAtomicPromotePattern` |
| security.py | (integrated into stash/retrieve tests) |
| caching.py | (integrated into retrieval tests) |

### Test Coverage Assessment

**Well-Covered Areas:**

- Working memory (stash/retrieve) - extensive coverage
- Pattern staging - comprehensive workflow tests
- Batch operations - edge cases covered
- Pub/Sub - threading and callback tests
- Streams/Timelines/Queues - feature-specific tests
- Error handling - failure scenarios covered
- Atomic transactions - critical path tests

**Areas Needing Attention During Extraction:**

- Security sanitization - tests embedded in stash tests
- Local caching - tests embedded in retrieval tests
- Cross-session coordination - separate test file exists

### Recommended Test Strategy During Refactoring

1. **Run tests after each module extraction**
2. **Keep test imports pointing to facade** (`from attune.memory.short_term import ...`)
3. **Add integration tests** for module interactions
4. **Verify no test regressions** with `pytest -v`
