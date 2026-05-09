---
type: error
name: codecov-patch-0-usually-means-tests-skipped-not-failed
confidence: Verified
tags: [ci, testing, imports, git]
source: .claude/CLAUDE.md
---

# Error: `codecov/patch` 0% usually means tests *skipped*, not
  failed

## Signature

. Fix by making the dep installable (add to `[dev]` or move to required), or by adding unconditional error-path tests that don't need the optional dep (use `sys.modules[name] = None` sentinel to exercise the

## Root Cause

The `codecov/patch` check measures coverage of the diff — new/changed lines. If new tests use `pytest.importorskip` on an optional dep that CI doesn't install, every assertion skips, and the diff shows 0% covered even though all tests "pass". Fix by making the dep installable (add to `[dev]` or move to required), or by adding unconditional error-path tests that don't need the optional dep (use `sys.modules[name] = None` sentinel to exercise the "missing extra" branches).

## Resolution

1. The `codecov/patch` check measures coverage of the diff — new/changed lines

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `codecov/patch` 0% usually means tests *skipped*, not
  failed
- Tip: Best practice: `codecov/patch` 0% usually means tests *skipped*, not
  failed
- Task: Update test mocks and assertions
