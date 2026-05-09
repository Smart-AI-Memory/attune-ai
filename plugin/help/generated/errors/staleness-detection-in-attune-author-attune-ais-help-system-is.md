---
type: error
name: staleness-detection-in-attune-author-attune-ais-help-system-is
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware

## Signature

Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware

## Root Cause

`check_staleness` reads `concept.md`'s `source_hash` frontmatter and compares it to the current source hash. Consequences: (1) if one template is manually edited but concept.md is unchanged, the drift is invisible; (2) if a feature has 3 templates where the standard is 11, staleness reports "current" as long as concept.md's hash matches — completeness is not checked; (3) deleting all templates except concept.md still reports "current." Implication: when fixing staleness problems (e.g. adding `--all-kinds` regeneration), verify behaviorally by running `attune-author status` before and after, and also grep the templates dir to confirm file counts match the kind count you expect. Don't trust the status report alone.

## Resolution

1. `check_staleness` reads `concept.md`'s `source_hash` frontmatter and compares it to the current source hash

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware
