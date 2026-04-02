---
type: error
name: list-workflows-deduplication-must-keep-base-names-visible
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `list_workflows()` deduplication must keep base names visible

## Signature

`list_workflows()` deduplication must keep base names visible

## Root Cause

When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP` (the explicit `-sdk` suffixed names). Do NOT also skip base names that have an SDK variant — those are the names users see and type. The resolver routes base names to SDK implementations transparently.

## Resolution

1. When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP` (the explicit `-sdk` suffixed names)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `list_workflows()` deduplication must keep base names visible
- Tip: Best practice: `list_workflows()` deduplication must keep base names visible
