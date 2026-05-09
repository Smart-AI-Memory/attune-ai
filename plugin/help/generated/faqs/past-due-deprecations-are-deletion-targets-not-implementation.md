---
type: faq
name: past-due-deprecations-are-deletion-targets-not-implementation
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about past-due deprecations are deletion targets, not implementation targets — read the DeprecationWarning before "fixing" the TODO?

## Answer

`ProgressiveTestGenWorkflow.__init__` raised a `DeprecationWarning` since v5.3.0 announcing removal in v6.0.0. The class carried through v6.0.x and v6.2.0 unchanged, with its `_execute_tier_impl` returning simulated (not LLM-generated) test data behind a `TODO(llm-integration)` comment.

```
ProgressiveTestGenWorkflow.__init__
```

## Related Topics
- **Error**: Detailed error: Past-due deprecations are deletion targets,
  not implementation targets — read the
  DeprecationWarning before "fixing" the TODO
