---
type: faq
name: staleness-detection-in-attune-author-attune-ais-help-system-is
source: .claude/CLAUDE.md
---

# FAQ: What should I know about staleness detection in attune-author/attune-ai's .help/ system is hash-based on a single representative file, not per-template or completeness-aware?

## Answer

`check_staleness` reads `concept.md`'s `source_hash` frontmatter and compares it to the current source hash. Consequences: (1) if one template is manually edited but concept.md is unchanged, the drift is invisible; (2) if a feature has 3 templates where the standard is 11, staleness reports "current" as long as concept.md's hash matches — completeness is not checked; (3) deleting all templates except concept.md still reports "current." Implication: when fixing staleness problems (e.g.

```
check_staleness
```

## Related Topics
- **Error**: Detailed error: Staleness detection in attune-author/attune-ai's
  `.help/` system is hash-based on a single representative
  file, not per-template or completeness-aware
