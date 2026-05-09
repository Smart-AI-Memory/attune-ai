---
type: warning
name: noqa-f401-re-exports-break-silently-on-satellite-file-deletion
confidence: Verified
tags: [security, imports, python]
source: .claude/CLAUDE.md
---

# Warning: `# noqa: F401` re-exports break silently on satellite file
  deletion

## Condition

SDK-native workflows re-export constants from legacy satellite files (e.g

## Risk

Deleting the satellite file breaks the import at runtime, not at lint time (ruff doesn't check import resolution)

## Mitigation

1. Before deleting any workflow satellite file, grep the parent workflow for `noqa: F401` imports from it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `# noqa: F401` re-exports break silently on satellite file
  deletion
