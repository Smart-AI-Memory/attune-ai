---
type: faq
name: enforce-admins-false-defeats-code-review-scorecard-check
tags: [ci]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about enforce_admins: false defeats Code-Review Scorecard check?

## Answer

Even with `required_approving_review_count: 1`, admins bypass reviews when `enforce_admins` is off. Scorecard sees 0/25 approved changesets.

```
required_approving_review_count: 1
```

## Related Topics
- **Error**: Detailed error: `enforce_admins: false` defeats Code-Review Scorecard check
