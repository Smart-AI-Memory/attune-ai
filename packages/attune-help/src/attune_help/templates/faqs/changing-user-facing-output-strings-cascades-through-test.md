---
type: faq
name: changing-user-facing-output-strings-cascades-through-test
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about changing user-facing output strings cascades through test assertions?

## Answer

Replacing "Workflow completed" with voice layer personality messaging broke 6 assertions across 4 test classes. When changing any user-facing output string in a shared path (like `_print_workflow_result`), grep the entire test suite for the old string before considering the change done.

```
_print_workflow_result
```

## Related Topics
- **Error**: Detailed error: Changing user-facing output strings cascades through test
  assertions
