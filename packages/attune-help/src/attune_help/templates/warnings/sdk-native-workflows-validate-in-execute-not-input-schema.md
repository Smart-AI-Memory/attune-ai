---
type: warning
name: sdk-native-workflows-validate-in-execute-not-input-schema
confidence: Verified
tags: [testing, security]
source: .claude/CLAUDE.md
---

# Warning: SDK-native workflows validate in `execute()`, not `input_schema`

## Condition

After merging to SDK-native, workflows no longer declare `input_schema` as a class attribute — path validation happens inside `execute()`

## Risk

Ignoring this guidance may cause: SDK-native workflows validate in `execute()`, not `input_schema`

## Mitigation

1. After merging to SDK-native, workflows no longer declare `input_schema` as a class attribute — path validation happens inside `execute()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: SDK-native workflows validate in `execute()`, not `input_schema`
