---
type: faq
name: mixin-classes-inherit-self-workspace-root-at-runtime-not-at
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about mixin classes inherit self._workspace_root at runtime, not at definition time?

## Answer

`WorkflowHandlersMixin` has no `__init__` and no `_workspace_root` attribute, but it works because it's mixed into `EmpathyMCPServer` which sets `_workspace_root` in its constructor. When adding validation to a mixin, use `self._workspace_root` freely — but document the expected host attribute in the mixin docstring.

```
WorkflowHandlersMixin
```

## Related Topics
- **Error**: Detailed error: Mixin classes inherit `self._workspace_root` at runtime,
  not at definition time
