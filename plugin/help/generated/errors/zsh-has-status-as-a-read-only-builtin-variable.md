---
type: error
name: zsh-has-status-as-a-read-only-builtin-variable
confidence: Verified
tags: [ci, testing, packaging]
source: .claude/CLAUDE.md
---

# Error: zsh has `status` as a read-only builtin variable

## Signature

zsh has `status` as a read-only builtin variable

## Root Cause

Shell scripts that do `status=$(...)` work in bash but fail in zsh with "read-only variable: status". Use `result=` or any other name instead. Relevant when writing Monitor/polling scripts that capture a command's output into a named variable — these often run under /bin/bash -e in CI, but shell defaults vary and the scripts may be invoked under zsh locally. Repo guard: `tests/unit/ci/test_zsh_readonly _assignments.py` scans all shell scripts + workflow YAMLs for the pattern and fails CI if any script assigns to `status`, `pipestatus`, or other zsh readonly names.

## Resolution

1. Use `result=` or any other name instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: zsh has `status` as a read-only builtin variable
- Task: Update test mocks and assertions
