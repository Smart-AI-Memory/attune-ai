---
type: warning
name: new-dataclass-fields-need-both-the-class-and-the-parser-updated
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: New dataclass fields need both the class AND the parser updated

## Condition

Adding a field (e.g

## Risk

If there's a `_parse_*()` helper that builds the dataclass from raw YAML/JSON, the field stays silently empty at runtime until the parser is also updated

## Mitigation

1. Adding a field (e.g
2. Always grep for the parser function when adding a new dataclass field

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: New dataclass fields need both the class AND the parser updated
