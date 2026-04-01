---
type: faq
name: bug-predict-dangerous-eval-flags-subprocess-exec
tags: [security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about bug-predict dangerous_eval flags subprocess_exec?

## Answer

The scanner's regex matches `create_subprocess_exec` as containing `exec`, producing a false positive for `dangerous_eval` in `hooks/executor.py`. There is no actual `eval()` or `exec()` usage.

**How to fix:**
- Always verify HIGH severity scanner findings against the source before treating them as real vulnerabilities

```
create_subprocess_exec
```

## Related Topics
- **Error**: Detailed error: Bug-predict `dangerous_eval` flags `subprocess_exec`
