---
type: warning
name: template-generators-overwrite-hand-written-files
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Template generators overwrite hand-written files

## Condition

The `generate_concept_templates.py` auto-discovery creates bland stubs that overwrite rich hand-written concept files

## Risk

Ignoring this guidance may cause: Template generators overwrite hand-written files

## Mitigation

1. check if the existing file has `auto-discovered` in its tags before overwriting — if not, it was hand-written and should be preserved

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Template generators overwrite hand-written files
