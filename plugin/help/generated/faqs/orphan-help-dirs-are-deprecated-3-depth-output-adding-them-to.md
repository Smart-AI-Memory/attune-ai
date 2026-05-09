---
type: faq
name: orphan-help-dirs-are-deprecated-3-depth-output-adding-them-to
tags: [security, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about orphan .help/ dirs are deprecated 3-depth output; adding them to features.yaml triggers regen that overwrites the content you wanted to preserve?

## Answer

the naive instinct when faced with orphan template dirs (`.help/templates/security/`, `.help/templates/workflows/` — both 3-kind leftovers from the in-repo 3-depth generator) is "add to manifest to keep them current." But attune-author's `--all-kinds` regen on the next weekly run overwrites all 3 files with 11 new ones — the "preservation" is imaginary. Also, broad-named orphans (`security`, `workflows`) collide with existing feature names (`security-audit`, individual workflow features) on RAG retrieval per the mutual- competition lesson.

```
.help/templates/security/
```

## Related Topics
- **Error**: Detailed error: Orphan .help/ dirs are deprecated 3-depth output;
  adding them to features.yaml triggers regen that
  overwrites the content you wanted to preserve
