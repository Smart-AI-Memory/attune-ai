---
type: error
name: hot-reload-subsystem-was-1-038-lines-of-dead-code
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: `hot_reload/` subsystem was 1,038 lines of dead code

## Signature

`hot_reload/` subsystem was 1,038 lines of dead code

## Root Cause

Zero inbound imports from any file outside the package, but it had its own test suite (1,409 lines) that all passed — making it look alive. Lesson: passing tests are not evidence of integration. Always grep for imports outside the module itself before considering a feature active. (This echoes the existing `socratic/embeddings/` lesson but for a different module.)

## Resolution

1. Always grep for imports outside the module itself before considering a feature active

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `hot_reload/` subsystem was 1,038 lines of dead code
- Task: Update test mocks and assertions
