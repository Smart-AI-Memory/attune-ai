---
type: error
name: mixin-classes-inherit-self-workspace-root-at-runtime-not-at
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Mixin classes inherit `self._workspace_root` at runtime,
  not at definition time

## Signature

Mixin classes inherit `self._workspace_root` at runtime,
  not at definition time

## Root Cause

`WorkflowHandlersMixin` has no `__init__` and no `_workspace_root` attribute, but it works because it's mixed into `EmpathyMCPServer` which sets `_workspace_root` in its constructor. When adding validation to a mixin, use `self._workspace_root` freely — but document the expected host attribute in the mixin docstring.

## Resolution

1. `WorkflowHandlersMixin` has no `__init__` and no `_workspace_root` attribute, but it works because it's mixed into `EmpathyMCPServer` which sets `_workspace_root` in its constructor

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Mixin classes inherit `self._workspace_root` at runtime,
  not at definition time
