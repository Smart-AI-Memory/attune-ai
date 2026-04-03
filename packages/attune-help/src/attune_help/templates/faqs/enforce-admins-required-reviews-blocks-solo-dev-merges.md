---
type: faq
name: enforce-admins-required-reviews-blocks-solo-dev-merges
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: Why does enforce_admins + required reviews blocks solo-dev merges?

## Answer

With `enforce_admins: true` and `required_approving_review_count: 1`, the repo owner cannot self-approve PRs (`Review Can not approve your own pull request`) and `--admin` merge also fails. The auto-approve workflow's `GITHUB_TOKEN` also can't approve the PR author's own PRs.

```
enforce_admins: true
```

## Related Topics
- **Error**: Detailed error: `enforce_admins` + required reviews blocks solo-dev merges
