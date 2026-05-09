---
type: warning
name: staleness-detection-in-attune-author-attune-ais-help-system-is
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware

## Condition

`check_staleness` reads `concept.md`'s `source_hash` frontmatter and compares it to the current source hash

## Risk

Ignoring this guidance may cause: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware

## Mitigation

1. Don't trust the status report alone

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware
