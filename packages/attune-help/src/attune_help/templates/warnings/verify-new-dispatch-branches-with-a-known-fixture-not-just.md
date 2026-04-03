---
type: warning
name: verify-new-dispatch-branches-with-a-known-fixture-not-just
confidence: Verified
tags: [testing, imports, git]
source: .claude/CLAUDE.md
---

# Warning: Verify new dispatch branches with a known fixture, not just
  imports

## Condition

When adding a new runtime case (e.g

## Risk

Ignoring this guidance may cause: Verify new dispatch branches with a known fixture, not just
  imports

## Mitigation

1. Run `Executor.run()` directly with a spec whose `runtime` matches the new case and assert `result.status == "success"` before considering the feature done

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Verify new dispatch branches with a known fixture, not just
  imports
