---
type: error
name: bug-predict-dangerous-eval-flags-subprocess-exec
confidence: Verified
tags: [security, claude-code]
source: .claude/CLAUDE.md
---

# Error: Bug-predict `dangerous_eval` flags `subprocess_exec`

## Signature

Bug-predict `dangerous_eval` flags `subprocess_exec`

## Root Cause

The scanner's regex matches `create_subprocess_exec` as containing `exec`, producing a false positive for `dangerous_eval` in `hooks/executor.py`. There is no actual `eval()` or `exec()` usage. Always verify HIGH severity scanner findings against the source before treating them as real vulnerabilities.

## Resolution

1. Always verify HIGH severity scanner findings against the source before treating them as real vulnerabilities

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Bug-predict `dangerous_eval` flags `subprocess_exec`
