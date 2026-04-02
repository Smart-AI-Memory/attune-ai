---
type: warning
name: hot-reload-subsystem-was-1-038-lines-of-dead-code
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: `hot_reload/` subsystem was 1,038 lines of dead code

## Condition

Zero inbound imports from any file outside the package, but it had its own test suite (1,409 lines) that all passed — making it look alive

## Risk

Ignoring this guidance may cause: `hot_reload/` subsystem was 1,038 lines of dead code

## Mitigation

1. Always grep for imports outside the module itself before considering a feature active

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `hot_reload/` subsystem was 1,038 lines of dead code
