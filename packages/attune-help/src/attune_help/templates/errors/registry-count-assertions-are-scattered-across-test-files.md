---
type: error
name: registry-count-assertions-are-scattered-across-test-files
confidence: Verified
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# Error: Registry count assertions are scattered across test files

## Signature

Registry count assertions are scattered across test files

## Root Cause

When merging SDK workflow variants (reducing `_SDK_WORKFLOW_MAP` from 12→9 entries), hardcoded count assertions like `assert len(_SDK_WORKFLOW_MAP) == 12` and expected-set assertions exist in routing behavioral tests, validation framework tests, and coverage batch tests. Always grep for the old count and old class names (e.g. `SecurityAuditAgentSDKWorkflow`) across all test files when changing registry size.

## Resolution

1. Always grep for the old count and old class names (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Registry count assertions are scattered across test files
- Task: Update test mocks and assertions
