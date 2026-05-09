---
type: faq
name: gh-api-x-patch-f-name-n-rejects-integers-as-strings
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does gh api -X PATCH ... -f name=N rejects integers as strings?

## Answer

`gh api` flag `-f` always sends string values, so `-f required_approving_review_count=1` produces a 422 error `"1" is not an integer`. Specifically matters for `branches/<name>/protection/required_pull_request_reviews` updates during the temp-remove-review/admin-merge/restore dance.

**How to fix:**
- Use `-F` instead — it infers the type (integer, boolean, etc.) from the value

```
 always sends string values, so
```

## Related Topics
- **Error**: Detailed error: `gh api -X PATCH ... -f name=N` rejects integers as
  strings
