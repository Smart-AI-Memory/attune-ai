---
type: warning
name: bug-predict-dangerous-eval-flags-subprocess-exec
confidence: Verified
tags: [security, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Bug-predict `dangerous_eval` flags `subprocess_exec`

## Condition

The scanner's regex matches `create_subprocess_exec` as containing `exec`, producing a false positive for `dangerous_eval` in `hooks/executor.py`

## Risk

Ignoring this guidance may cause: Bug-predict `dangerous_eval` flags `subprocess_exec`

## Mitigation

1. Always verify HIGH severity scanner findings against the source before treating them as real vulnerabilities

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Bug-predict `dangerous_eval` flags `subprocess_exec`
