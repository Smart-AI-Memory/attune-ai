---
type: error
name: verify-new-dispatch-branches-with-a-known-fixture-not-just
confidence: Verified
tags: [testing, imports, git]
source: .claude/CLAUDE.md
---

# Error: Verify new dispatch branches with a known fixture, not just
  imports

## Signature

Verify new dispatch branches with a known fixture, not just
  imports

## Root Cause

When adding a new runtime case (e.g. `local_python`) to an existing dispatch table, a clean import doesn't prove the branch fires. Run `Executor.run()` directly with a spec whose `runtime` matches the new case and assert `result.status == "success"` before considering the feature done.

## Resolution

1. Run `Executor.run()` directly with a spec whose `runtime` matches the new case and assert `result.status == "success"` before considering the feature done

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
