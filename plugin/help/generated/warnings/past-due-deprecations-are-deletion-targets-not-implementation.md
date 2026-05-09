---
type: warning
name: past-due-deprecations-are-deletion-targets-not-implementation
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: Past-due deprecations are deletion targets,
  not implementation targets — read the
  DeprecationWarning before "fixing" the TODO

## Condition

`ProgressiveTestGenWorkflow.__init__` raised a `DeprecationWarning` since v5.3.0 announcing removal in v6.0.0

## Risk

When the TODO was triaged as a blocker, the instinct was "wire the LLM." The better answer once the deprecation comment was read: "honor the removal promise" — delete the file, its tests, and its demo

## Mitigation

1. `ProgressiveTestGenWorkflow.__init__` raised a `DeprecationWarning` since v5.3.0 announcing removal in v6.0.0

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Past-due deprecations are deletion targets,
  not implementation targets — read the
  DeprecationWarning before "fixing" the TODO
