---
type: faq
name: prompt-template-word-wrap-silently-breaks-single-line-substring
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: Why does prompt-template word wrap silently breaks single-line substring assertions in tests?

## Answer

a template with a sentence like "The provided context does not\ncover this question." passes `"The provided context" in out` but fails `"context does not cover" in out` because the phrase straddles a newline. Hit while adding the `strict` prompt variant in attune-rag.

**How to fix:**
- normalize whitespace at the assertion boundary with `" ".join(out.split())`, or pick a substring that cannot wrap

```
"The provided context" in out
```

## Related Topics
- **Error**: Detailed error: Prompt-template word wrap silently breaks single-line
  substring assertions in tests
