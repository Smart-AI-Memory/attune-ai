---
type: warning
name: zsh-has-status-as-a-read-only-builtin-variable
confidence: Verified
tags: [ci, testing, packaging]
source: .claude/CLAUDE.md
---

# Warning: zsh has `status` as a read-only builtin variable

## Condition

Shell scripts that do `status=$(...)` work in bash but fail in zsh with "read-only variable: status"

## Risk

Shell scripts that do `status=$(...)` work in bash but fail in zsh with "read-only variable: status"

## Mitigation

1. Use `result=` or any other name instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: zsh has `status` as a read-only builtin variable
