---
type: warning
name: list-workflows-deduplication-must-keep-base-names-visible
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: `list_workflows()` deduplication must keep base names visible

## Condition

When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP` (the explicit `-sdk` suffixed names)

## Risk

Ignoring this guidance may cause: `list_workflows()` deduplication must keep base names visible

## Mitigation

1. When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP` (the explicit `-sdk` suffixed names)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `list_workflows()` deduplication must keep base names visible
