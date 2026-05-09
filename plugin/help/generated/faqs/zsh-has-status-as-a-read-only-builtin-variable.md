---
type: faq
name: zsh-has-status-as-a-read-only-builtin-variable
tags: [ci, testing, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about zsh has status as a read-only builtin variable?

## Answer

Shell scripts that do `status=$(...)` work in bash but fail in zsh with "read-only variable: status". Relevant when writing Monitor/polling scripts that capture a command's output into a named variable — these often run under /bin/bash -e in CI, but shell defaults vary and the scripts may be invoked under zsh locally.

**How to fix:**
- Use `result=` or any other name instead

```
status=$(...)
```

## Related Topics
- **Error**: Detailed error: zsh has `status` as a read-only builtin variable
