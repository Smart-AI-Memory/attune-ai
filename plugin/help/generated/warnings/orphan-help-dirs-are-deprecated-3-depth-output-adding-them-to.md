---
type: warning
name: orphan-help-dirs-are-deprecated-3-depth-output-adding-them-to
confidence: Verified
tags: [security, git]
source: .claude/CLAUDE.md
---

# Warning: Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve

## Condition

the naive instinct when faced with orphan template dirs (`.help/templates/security/`, `.help/templates/workflows/` — both 3-kind leftovers from the in-repo 3-depth generator) is "add to manifest to keep them current." But attune-author's `--all-kinds` regen on the next weekly run overwrites all 3 files with 11 new ones — the "preservation" is imaginary

## Risk

Ignoring this guidance may cause: Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve

## Mitigation

1. the naive instinct when faced with orphan template dirs (`.help/templates/security/`, `.help/templates/workflows/` — both 3-kind leftovers from the in-repo 3-depth generator) is "add to manifest to keep them current." But attune-author's `--all-kinds` regen on the next weekly run overwrites all 3 files with 11 new ones — the "preservation" is imaginary

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve
