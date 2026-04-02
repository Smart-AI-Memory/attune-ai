---
type: error
name: new-dataclass-fields-need-both-the-class-and-the-parser-updated
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: New dataclass fields need both the class AND the parser updated

## Signature

New dataclass fields need both the class AND the parser updated

## Root Cause

Adding a field (e.g. `local_python`) to a dataclass only updates the in-memory model. If there's a `_parse_*()` helper that builds the dataclass from raw YAML/JSON, the field stays silently empty at runtime until the parser is also updated. Always grep for the parser function when adding a new dataclass field.

## Resolution

1. Adding a field (e.g
2. Always grep for the parser function when adding a new dataclass field

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: New dataclass fields need both the class AND the parser updated
