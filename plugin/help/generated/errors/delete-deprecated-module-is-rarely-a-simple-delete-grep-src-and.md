---
type: error
name: delete-deprecated-module-is-rarely-a-simple-delete-grep-src-and
confidence: Verified
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: "Delete deprecated module" is rarely a simple
  delete — grep src/ AND tests/ first

## Signature

"Delete deprecated module" is rarely a simple
  delete — grep src/ AND tests/ first

## Root Cause

the in-repo `attune.help.generator` 3-depth generator looked like dead code on first glance but had 3 live source consumers (MCP `help_update` handler, `help/maintenance.py`, `help/engine.py`) plus multiple test imports. A straight `rm` would have broken the `help_update` MCP tool. Intermediate step that closes the "orphan recurrence" risk without the migration cost: module-level docstring note + `warnings.warn(..., Deprecation Warning, stacklevel=2)` at the top of the public entry point. Pytest's default `ignore::DeprecationWarning` means zero test impact; future callers surface audibly via `python -W default::DeprecationWarning`. Reserve actual deletion for when all consumers have migrated.

## Resolution

1. the in-repo `attune.help.generator` 3-depth generator looked like dead code on first glance but had 3 live source consumers (MCP `help_update` handler, `help/maintenance.py`, `help/engine.py`) plus multiple test imports

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
