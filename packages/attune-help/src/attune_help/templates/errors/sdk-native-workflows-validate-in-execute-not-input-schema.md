---
type: error
name: sdk-native-workflows-validate-in-execute-not-input-schema
confidence: Verified
tags: [testing, security]
source: .claude/CLAUDE.md
---

# Error: SDK-native workflows validate in `execute()`, not `input_schema`

## Signature

SDK-native workflows validate in `execute()`, not `input_schema`

## Root Cause

After merging to SDK-native, workflows no longer declare `input_schema` as a class attribute — path validation happens inside `execute()`. Tests asserting `Workflow.input_schema is not None` must be removed or updated.

## Resolution

1. After merging to SDK-native, workflows no longer declare `input_schema` as a class attribute — path validation happens inside `execute()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
