---
type: warning
name: codecov-patch-0-usually-means-tests-skipped-not-failed
confidence: Verified
tags: [ci, testing, imports, git]
source: .claude/CLAUDE.md
---

# Warning: `codecov/patch` 0% usually means tests *skipped*, not
  failed

## Condition

The `codecov/patch` check measures coverage of the diff — new/changed lines

## Risk

Fix by making the dep installable (add to `[dev]` or move to required), or by adding unconditional error-path tests that don't need the optional dep (use `sys.modules[name] = None` sentinel to exercise the "missing extra" branches)

## Mitigation

1. The `codecov/patch` check measures coverage of the diff — new/changed lines

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `codecov/patch` 0% usually means tests *skipped*, not
  failed
