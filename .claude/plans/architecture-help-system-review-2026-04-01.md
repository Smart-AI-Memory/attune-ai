# Help System Architecture Review

**Created:** 2026-04-01
**Source:** /plan architecture
**Route:** architecture
**Status:** completed

## Problem

The help system was built rapidly across one session.
It works end-to-end but has accumulated architectural
debt: engine.py has 8+ responsibilities in one file,
session state has no concurrency protection, cross-
links are loaded from disk on every call, and the
maintenance workflow doesn't validate subprocess
results.

## Findings (by severity)

### Critical

| Issue | Location | Impact |
|-------|----------|--------|
| 8+ responsibilities in engine.py (989 lines) | engine.py | Hard to test, maintain, or extend |
| Race condition in `_session_state` | engine.py:417-475 | Data loss under concurrent sessions |

### High

| Issue | Location | Impact |
|-------|----------|--------|
| Cross-links loaded from disk on every `populate()` call | engine.py:204-252 | Unnecessary I/O, no caching |
| Subprocess results silently ignored in maintenance workflow | help_maintenance.py:196-208 | Reports success on failure |
| No source path validation in maintenance workflow MAP phase | help_maintenance.py:142 | Traversal via manifest |

### Medium

| Issue | Location | Impact |
|-------|----------|--------|
| `_extract_topic("")` returns empty string, breaks depth tracking | engine.py:478 | Wrong escalation on edge cases |
| Hook scripts have no timeout enforcement | hooks/ | Could hang under pathological input |
| MCP help handlers diverge from other handler patterns | server.py:543-653 | Inconsistent error handling |
| Manifest silently skips templates without `source` field | generate_all.py:117-118 | Invisible coverage gaps |

## Recommendations

### Priority 1: Harden What Exists (before v5.2 release)

These are targeted fixes, not refactors — they address
security and correctness without restructuring.

1. **Add threading lock to session state**
   - Add `_SESSION_LOCK = threading.RLock()` to engine.py
   - Wrap `_load_session`, `_persist_session`,
     `populate_progressive`, `reset_session` in lock
   - ~15 lines changed

2. **Cache cross-links at module level**
   - Add `_CROSS_LINKS_CACHE` dict keyed by path
   - Load once, reuse for session lifetime
   - ~10 lines changed

3. **Validate subprocess exit codes in
   HelpMaintenanceWorkflow**
   - Change `check=False` to `check=True` with
     CalledProcessError handling
   - Track `failed` list alongside `regenerated`
   - Return `failed` in output dict

4. **Add path containment to maintenance MAP phase**
   - Add `source_path.resolve().relative_to(repo)`
     check before hashing
   - Matches the pattern from `_find_template_file`

5. **Guard `_extract_topic` against empty results**
   - Return `None` if extracted topic is empty
   - Check in `populate_progressive` before proceeding

### Priority 2: Split Engine Module (v5.3 refactor)

Split engine.py into focused modules under
`src/attune/help/`:

```
src/attune/help/
  __init__.py         # Re-exports for backward compat
  templates.py        # Loading, parsing, resolution
  audience.py         # Adaptation profiles
  progression.py      # Type-driven depth, topic extract
  session.py          # State persistence with locking
  workflows.py        # Chain prediction, precursors
  feedback.py         # Rating, confidence scoring
  engine.py           # Thin facade: populate() calls
```

This is a refactor — no new features, just cleaner
boundaries. Each module gets its own test file.

### Priority 3: Harden Hooks (nice-to-have)

- Cap stdin read to 10KB in `help_on_error.py`
- Add SIGALRM timeout to `help_freshness_check.py`
- Limit manifest entries checked to 50 (sample)

## Scope

- **Files (Priority 1):** engine.py, help_maintenance.py,
  server.py
- **Files (Priority 2):** Split engine.py into 7 modules
- **Type:** architecture

## Decisions (from review)

- **Split engine.py now** — yes, do it as part of
  Priority 2 in this pass
- **Concurrent sessions is real** — multiple tabs or
  two subscriptions on same machine. Threading lock
  is mandatory.
- **Maintenance workflow should commit** — auto-commit
  regenerated templates after validation passes
