---
type: warning
name: registry-count-assertions-are-scattered-across-test-files
confidence: Verified
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# Warning: Registry count assertions are scattered across test files

## Condition

When merging SDK workflow variants (reducing `_SDK_WORKFLOW_MAP` from 12→9 entries), hardcoded count assertions like `assert len(_SDK_WORKFLOW_MAP) == 12` and expected-set assertions exist in routing behavioral tests, validation framework tests, and coverage batch tests

## Risk

Ignoring this guidance may cause: Registry count assertions are scattered across test files

## Mitigation

1. Always grep for the old count and old class names (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Registry count assertions are scattered across test files
