---
type: error
name: past-due-deprecations-are-deletion-targets-not-implementation
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Past-due deprecations are deletion targets,
  not implementation targets — read the
  DeprecationWarning before "fixing" the TODO

## Signature

DeprecationWarning

## Root Cause

`ProgressiveTestGenWorkflow.__init__` raised a `DeprecationWarning` since v5.3.0 announcing removal in v6.0.0. The class carried through v6.0.x and v6.2.0 unchanged, with its `_execute_tier_impl` returning simulated (not LLM-generated) test data behind a `TODO(llm-integration)` comment. When the TODO was triaged as a blocker, the instinct was "wire the LLM." The better answer once the deprecation comment was read: "honor the removal promise" — delete the file, its tests, and its demo. Preserve the migration alias (`progressive-test-gen -> test-gen`) so CLI users keep working. Generalization: before spending effort to complete a placeholder, check whether the containing class is already deprecated with a stated removal date — a past-due deprecation makes implementation strictly wrong.

## Resolution

1. `ProgressiveTestGenWorkflow.__init__` raised a `DeprecationWarning` since v5.3.0 announcing removal in v6.0.0

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Past-due deprecations are deletion targets,
  not implementation targets — read the
  DeprecationWarning before "fixing" the TODO
- Task: Update test mocks and assertions
