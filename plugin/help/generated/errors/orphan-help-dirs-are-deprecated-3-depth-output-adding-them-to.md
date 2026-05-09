---
type: error
name: orphan-help-dirs-are-deprecated-3-depth-output-adding-them-to
confidence: Verified
tags: [security, git]
source: .claude/CLAUDE.md
---

# Error: Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve

## Signature

Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve

## Root Cause

the naive instinct when faced with orphan template dirs (`.help/templates/security/`, `.help/templates/workflows/` — both 3-kind leftovers from the in-repo 3-depth generator) is "add to manifest to keep them current." But attune-author's `--all-kinds` regen on the next weekly run overwrites all 3 files with 11 new ones — the "preservation" is imaginary. Also, broad-named orphans (`security`, `workflows`) collide with existing feature names (`security-audit`, individual workflow features) on RAG retrieval per the mutual- competition lesson. Correct path: delete the orphan dirs. Git history is the archive.

## Resolution

1. the naive instinct when faced with orphan template dirs (`.help/templates/security/`, `.help/templates/workflows/` — both 3-kind leftovers from the in-repo 3-depth generator) is "add to manifest to keep them current." But attune-author's `--all-kinds` regen on the next weekly run overwrites all 3 files with 11 new ones — the "preservation" is imaginary

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
