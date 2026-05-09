---
type: error
name: noqa-f401-re-exports-break-silently-on-satellite-file-deletion
confidence: Verified
tags: [security, imports, python]
source: .claude/CLAUDE.md
---

# Error: `# noqa: F401` re-exports break silently on satellite file
  deletion

## Signature

`# noqa: F401` re-exports break silently on satellite file
  deletion

## Root Cause

SDK-native workflows re-export constants from legacy satellite files (e.g. `from .security_audit_patterns import SECURITY_PATTERNS  # noqa: F401`). Deleting the satellite file breaks the import at runtime, not at lint time (ruff doesn't check import resolution). Before deleting any workflow satellite file, grep the parent workflow for `noqa: F401` imports from it. Also check `__all__` — it may reference the re-exported names.

## Resolution

1. SDK-native workflows re-export constants from legacy satellite files (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
