# Phase 3D: Memory/Telemetry Split - Core vs Optional (Redis)

**Status:** COMPLETE
**Sessions:** 5
**Created:** 2026-02-13
**Last Updated:** 2026-02-13

---

## Goal

Split memory and telemetry modules into:

- **Core** (always available): File-based storage, works without Redis
- **Optional** (needs Redis): Short-term memory, agent coordination, event streaming

---

## Current State: Implementation Complete

### What Was Already in Place (Pre-Phase 3D)

1. **pyproject.toml** - Redis in optional dependencies:

   ```toml
   [project.optional-dependencies]
   memory = ["redis>=5.0.0,<8.0.0"]
   ```

2. **memory/`__init__`.py** - Has `is_redis_available()` function

3. **unified.py** - File-first architecture already implemented:

   ```python
   file_session_enabled: bool = True   # Use file-based session as primary
   redis_auto_start: bool = False      # File-first by default
   redis_required: bool = False        # Graceful degradation
   ```

### What Phase 3D Added

1. **Feature Availability API** - `MemoryFeatures` and `TelemetryFeatures` classes
2. **Graceful degradation guards** - `require_redis()` calls in Redis-dependent modules
3. **Comprehensive documentation** - `docs/FEATURES.md` (540 lines)
4. **Full test coverage** - 40 tests across 3 test files

---

## Module Split

### Memory Module

#### CORE (Always Available) - 14 files

| Component | File | Description |
|-----------|------|-------------|
| File session storage | `file_session.py` | File-based session memory |
| Long-term memory | `long_term.py` | Persistent pattern storage |
| Storage backend | `storage_backend.py` | MemDocsStorage (file-based) |
| Graph structures | `nodes.py`, `edges.py`, `graph.py` | Data structures (no I/O) |
| Security | `security/` | PII scrubbing, secrets detection, audit logging |
| Encryption | `encryption.py` | AES-256-GCM encryption |
| Simple storage | `simple_storage.py` | Basic storage interface |
| Feature checking | `features.py` | `MemoryFeatures` API |

#### OPTIONAL (Requires Redis) - 23 files

| Component | File | Description |
|-----------|------|-------------|
| Redis bootstrap | `redis_bootstrap.py` | Redis startup and connection |
| Short-term memory | `short_term/` (15 modules) | Redis-based working memory with TTL |
| Cross-session coord | `cross_session.py` | Multi-session coordination |
| Redis config | `config.py` | Redis connection helpers |
| Control panel | `control_panel*.py` | Dashboard features (uses Redis) |

### Telemetry Module

#### CORE (Always Available) - 7 files

| Component | File | Description |
|-----------|------|-------------|
| Usage tracking | `usage_tracker.py` | File-based JSON Lines tracking |
| Feedback loop | `feedback_loop.py` | Quality feedback (file-based) |
| CLI commands | `cli*.py` | Command-line interface |
| Feature checking | `features.py` | `TelemetryFeatures` API |

#### OPTIONAL (Requires Redis) - 4 files

| Component | File | Description |
|-----------|------|-------------|
| Event streaming | `event_streaming.py` | Redis Streams for real-time events |
| Agent heartbeats | `agent_tracking.py` | TTL-based liveness monitoring |
| Agent coordination | `agent_coordination.py` | Inter-agent signaling |
| Approval gates | `approval_gates.py` | Workflow approval via Redis |

---

## Implementation Tasks

### Task 1: Feature Availability API - COMPLETE

**Files created:**

- `src/attune/memory/features.py` (214 lines) - `MemoryFeatures` class
- `src/attune/telemetry/features.py` (163 lines) - `TelemetryFeatures` class

**API surface:**

| Method | Purpose |
|--------|---------|
| `is_redis_available()` | Check if redis package is importable |
| `is_redis_running(host, port)` | Ping Redis server (memory only) |
| `get_feature_status(feature)` | Get `FeatureInfo` with status + install instructions |
| `require_redis(feature_name)` | Raise `ImportError` with helpful message if unavailable |
| `list_all_features()` | Dict of all features with their status |

**Status types:** `AVAILABLE`, `MISSING_DEPENDENCY`, `NOT_CONFIGURED`, `DISABLED`

### Task 2: Update Redis-Dependent Modules - COMPLETE

**Pattern applied:**

```python
from attune.memory.features import MemoryFeatures

def __init__(self, ...):
    MemoryFeatures.require_redis("Short-term memory")
    # ... rest of init
```

**Files updated:**

- `src/attune/memory/cross_session.py` - Added `require_redis()` in `__init__`
- `src/attune/memory/short_term/facade.py` - Imports `MemoryFeatures`
- `src/attune/telemetry/event_streaming.py` - Imports `TelemetryFeatures`
- `src/attune/memory/__init__.py` - Exports `MemoryFeatures`, `FeatureInfo`, `FeatureStatus`
- `src/attune/telemetry/__init__.py` - Exports `TelemetryFeatures`, `FeatureInfo`, `FeatureStatus`

**Graceful degradation patterns in use:**

| Module | Pattern | Behavior Without Redis |
|--------|---------|----------------------|
| `UnifiedMemory` | Auto-fallback | Uses `FileSessionMemory` transparently |
| `EventStreamer` | Silent degradation | Returns empty string `""` |
| `HeartbeatCoordinator` | Warn and skip | Logs warning, methods are no-ops |
| `CrossSessionCoordinator` | Strict guard | Raises `ImportError` with install instructions |
| `RedisShortTermMemory` | Strict guard | Raises `ImportError` with install instructions |

### Task 3: CLI Feature Status Command - COMPLETE

**Files:**

- `src/attune/cli_commands/utility_commands.py` - `cmd_features()` (lines 280-339)
- `src/attune/cli_minimal.py` - Registered as `features` subcommand (line 233, routed at 306-307)

**Usage:** `python -m attune.cli_minimal features` or `attune features`

**Output format:** Grouped tables with status icons, install instructions for missing deps, and Redis setup guidance.

**Bug fixed:** `FeatureStatus` enum was imported only from `attune.memory.features`, causing cross-enum `==` comparison to fail for telemetry features. Core telemetry features showed `⚠️` instead of `✅`. Fixed by comparing on `info.status.value == "available"` (string) instead of enum identity.

### Task 4: Documentation Updates - COMPLETE

**Files created/updated:**

- `docs/FEATURES.md` (540 lines) - Comprehensive feature availability guide with:
  - Core vs optional feature tables
  - Python API examples
  - CLI usage examples
  - Graceful degradation explanations
  - Redis setup guides (macOS, Linux, Docker, Windows)
  - Troubleshooting section
  - Feature comparison matrix
  - API reference
  - Migration guide (v2.6.3 -> v2.6.4+)

### Task 5: Testing - COMPLETE

**Test files created:**

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/test_memory_features.py` | 16 | All passing |
| `tests/unit/test_telemetry_features.py` | 13 | All passing |
| `tests/integration/test_graceful_degradation.py` | 11 | All passing |

**Coverage areas:**

- Redis availability checking (with/without package)
- Feature status for core vs Redis features
- `require_redis()` raising helpful errors
- `list_all_features()` completeness and consistency
- `FileSessionMemory` works without Redis
- `RedisShortTermMemory` requires Redis with helpful error
- `CrossSessionCoordinator` requires Redis
- `UnifiedMemory` auto-fallback to `FileSessionMemory`
- `EventStreamer` returns empty string without Redis
- `HeartbeatCoordinator` handles no memory gracefully
- `UsageTracker` works without Redis (file-based)

### Task 6: CHANGELOG Update - NEEDS VERIFICATION

The CHANGELOG.md was modified (per git status) but should be verified to include Phase 3D entries.

---

## Remaining Work

| Item                                            | Priority | Effort | Status                              |
| ----------------------------------------------- | -------- | ------ | ----------------------------------- |
| Verify CHANGELOG entries                        | Low      | 15 min | Needs review                        |
| Update modular-architecture-evolution.md status | Low      | 5 min  | Shows "READY", should be "COMPLETE" |
| Commit all new/modified files                   | High     | 10 min | Untracked/unstaged                  |

---

## Files Summary

### New Files (Untracked)

| File | Lines | Purpose |
|------|-------|---------|
| `src/attune/memory/features.py` | 214 | `MemoryFeatures` API |
| `src/attune/telemetry/features.py` | 163 | `TelemetryFeatures` API |
| `tests/unit/test_memory_features.py` | 169 | Unit tests (16 tests) |
| `tests/unit/test_telemetry_features.py` | ~130 | Unit tests (13 tests) |
| `tests/integration/test_graceful_degradation.py` | 220 | Integration tests (11 tests) |
| `docs/FEATURES.md` | 540 | Feature availability documentation |

### Modified Files

| File | Change |
|------|--------|
| `src/attune/memory/__init__.py` | Export `MemoryFeatures`, `FeatureInfo`, `FeatureStatus` |
| `src/attune/memory/cross_session.py` | Added `require_redis()` guard |
| `src/attune/memory/short_term/facade.py` | Import `MemoryFeatures` |
| `src/attune/telemetry/__init__.py` | Export `TelemetryFeatures`, `FeatureInfo`, `FeatureStatus` |
| `src/attune/telemetry/event_streaming.py` | Import `TelemetryFeatures` |

---

## Verification Checklist

- [x] `MemoryFeatures.is_redis_available()` works
- [x] `MemoryFeatures.get_feature_status()` returns correct status for core features
- [x] `MemoryFeatures.get_feature_status()` returns `MISSING_DEPENDENCY` when Redis unavailable
- [x] `MemoryFeatures.require_redis()` raises `ImportError` with install instructions
- [x] `TelemetryFeatures` API mirrors `MemoryFeatures` API
- [x] `UnifiedMemory` falls back to `FileSessionMemory` when Redis unavailable
- [x] `EventStreamer` degrades gracefully (returns empty string)
- [x] `HeartbeatCoordinator` degrades gracefully (logs warning)
- [x] `CrossSessionCoordinator` raises helpful `ImportError`
- [x] All 40 tests pass
- [x] Documentation updated (`docs/FEATURES.md`)
- [x] `attune features` CLI command wired up (bug fixed: cross-enum comparison)
- [ ] CHANGELOG.md includes Phase 3D entries
- [ ] All files committed

---

## Migration Impact

**Breaking changes:** None - all changes are additive

**New APIs:**

- `attune.memory.features.MemoryFeatures`
- `attune.memory.features.FeatureInfo`
- `attune.memory.features.FeatureStatus`
- `attune.telemetry.features.TelemetryFeatures`
- `attune.telemetry.features.FeatureInfo`
- `attune.telemetry.features.FeatureStatus`

**Users benefit from:**

- Clear understanding of what requires Redis vs what works out of the box
- Helpful error messages with `pip install` commands when Redis features are used without Redis
- Automatic fallback in `UnifiedMemory` - no config needed
- Comprehensive `docs/FEATURES.md` guide
