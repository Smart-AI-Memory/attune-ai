---
description: ADR-001: Workflow Engine Architecture Review: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# ADR-001: Workflow Engine Architecture Review

## Status

**Accepted with Revision** - January 25, 2026

### Revision History

- **Initial**: Decided to keep BaseWorkflow as-is
- **Revision 1**: Implemented CachingMixin extraction
- **Revision 2**: Implemented TelemetryMixin extraction; decided to skip ProgressMixin and TierTrackingMixin (too minimal)

## Implementation (Revised Decision)

After the initial review, the user reconsidered the "keep as-is" decision due to **future scaling concerns**. The team implemented the first phase of mixin extraction.

### CachingMixin Extraction (Completed)

**Files created/modified:**

- **NEW**: `src/attune/workflows/caching.py` - CachingMixin class
- **MODIFIED**: `src/attune/workflows/base.py` - Now inherits from CachingMixin

**What was extracted:**

| Component | From | To |
|-----------|------|-----|
| `_maybe_setup_cache()` | BaseWorkflow | CachingMixin |
| `_try_cache_lookup()` | inline in `_call_llm()` | CachingMixin |
| `_store_in_cache()` | inline in `_call_llm()` | CachingMixin |
| `_get_cache_type()` | inline | CachingMixin |
| `_get_cache_stats()` | inline in cost report | CachingMixin |

**Benefits achieved:**

1. **Cleaner `_call_llm()`**: Reduced from ~150 lines to ~50 lines for cache logic
2. **Reusable mixin**: CachingMixin can be used by other classes
3. **Testable in isolation**: Cache behavior can be tested independently
4. **No breaking changes**: All 50 workflow tests pass

**Test results:**

```text
tests/unit/test_workflow_base.py: 10 passed
tests/unit/workflows/test_workflow_execution.py: 40 passed
```

### TelemetryMixin Extraction (Completed)

**Files created/modified:**

- **NEW**: `src/attune/workflows/telemetry_mixin.py` - TelemetryMixin class
- **MODIFIED**: `src/attune/workflows/base.py` - Now inherits from TelemetryMixin

**What was extracted:**

| Component | From | To |
|-----------|------|-----|
| `_init_telemetry()` | inline in `__init__` | TelemetryMixin |
| `_track_telemetry()` | BaseWorkflow method | TelemetryMixin |
| `_emit_call_telemetry()` | BaseWorkflow method | TelemetryMixin |
| `_emit_workflow_telemetry()` | BaseWorkflow method | TelemetryMixin |
| `_generate_run_id()` | new helper | TelemetryMixin |

**Benefits achieved:**

1. **Removed ~100 lines** from BaseWorkflow
2. **Better null-safety**: Mixin has proper None checks for `_telemetry_backend`
3. **Reusable**: TelemetryMixin can be used by other classes needing telemetry
4. **No breaking changes**: All 50 workflow tests pass

### Skipped Extractions

| Concern | Lines | Decision | Reason |
|---------|-------|----------|--------|
| ProgressMixin | ~20 | **Skip** | Already well-encapsulated in `ProgressTracker` class; just callback invocations |
| TierTrackingMixin | ~15 | **Skip** | Too minimal; just initialization and a few method calls |

**Total code reduction:** ~150 lines removed from BaseWorkflow through mixin extraction.

## Context

The Attune AI workflow engine (`src/attune/workflows/`) was reviewed for architectural health. The review focused on:

- **BaseWorkflow** class complexity (2300+ lines)
- **Workflow registry** and discovery system
- **History persistence** mechanisms
- **Type system** (enum definitions)

### Deployment Context

Current deployment scenario: **Local development only**

This context influenced the priority of identified issues.

## Decision

After Socratic exploration, the following architectural decisions were made:

### 1. BaseWorkflow Complexity

**Decision:** Keep the current design with documentation of technical debt.

**Rationale:**
- The class is modified "sometimes" (not frequently enough to justify large refactor)
- Public API is simple (subclasses only override `run_stage`)
- Internal complexity is hidden from workflow authors
- Refactoring cost exceeds current pain

**Future consideration:** Progressive extraction via mixins if maintenance burden increases.

### 2. Dual Enum Definitions

**Issue:** `ModelTier` is defined in both:
- `src/attune/models/registry.py:20` (canonical)
- `src/attune/workflows/base.py:83` (backward compatibility)

**Decision:** Document as technical debt; add deprecation warning to `workflows.base.ModelTier`.

**Action items:**
- Add comment to `base.py` directing to canonical location
- Consider removing local enum in next major version (v5.0)

### 3. File-Based Workflow History

**Issue:** JSON file storage at `.empathy/workflow_runs.json` has limitations:
- No concurrent access handling
- Linear scan for stats queries
- No filtering capability

**Decision:** Document limitation; defer fix until pain is experienced.

**Rationale:** For local development only, JSON is sufficient. Migration to SQLite is a reasonable future enhancement if:
- Concurrent workflow execution causes corruption
- Query performance becomes noticeable

**Recommended future path:**
```
JSON (current) → SQLite (single-user scale) → PostgreSQL (team/production)
```

## Consequences

### Positive

- No immediate refactoring effort required
- Technical debt is documented for future teams
- Clear upgrade path exists when scaling needs arise
- Architectural patterns are validated through Socratic review

### Negative

- Technical debt persists (dual enums, god class)
- New developers may be confused by `ModelTier` duplication
- History system won't scale without future work

### Neutral

- This ADR serves as reference for future architectural discussions
- Decisions can be revisited if deployment scenario changes

## Red Flags Identified

| Issue | Severity | File | Recommended Action |
|-------|----------|------|-------------------|
| Dual `ModelTier` enums | MEDIUM | `workflows/base.py:83` | Deprecation warning |
| File-based history | HIGH (for production) | `workflows/base.py:217-282` | SQLite migration when needed |
| God class pattern | MEDIUM | `workflows/base.py` | Mixin extraction when pain increases |
| 12+ constructor params | LOW | `workflows/base.py:396` | Builder pattern as optional enhancement |

## Alternatives Considered

### For BaseWorkflow Complexity

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Keep as-is | No refactoring risk | Complexity grows | **Selected** |
| Composition | Clear responsibilities | Breaking changes | Deferred |
| Strategy pattern | Pluggable behaviors | Over-engineering | Rejected |
| Mixin extraction | Incremental, low risk | Temporary duplication | Future option |

### For History Storage

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| JSON (current) | Zero setup | No concurrency | **Selected for now** |
| SQLite | Queryable, concurrent-safe | Migration effort | Future option |
| Redis | Team visibility | Requires server | Not needed (local only) |
| PostgreSQL | Production-grade | Heavy for local dev | Rejected |

## Related Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [workflows/base.py](../../src/attune/workflows/base.py) - BaseWorkflow implementation
- [models/registry.py](../../src/attune/models/registry.py) - Canonical ModelTier definition

## Review Notes

This ADR was created through an interactive Socratic architecture review session using the `/agent` hub's **architect** agent. The review followed guided questioning to help discover insights rather than prescribing solutions.

### Key Socratic Questions Explored

1. "If a new developer needed to modify caching behavior, how many files would they need to understand?"
2. "What's the one reason BaseWorkflow would change?"
3. "If your team runs workflows in CI/CD pipelines across multiple containers, where does the history go?"

---

**Author:** Architect Agent (Attune AI)
**Reviewed:** January 25, 2026
**Next Review:** When deployment scenario changes or maintenance pain increases
