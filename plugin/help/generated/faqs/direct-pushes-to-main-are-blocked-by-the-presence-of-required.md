---
type: faq
name: direct-pushes-to-main-are-blocked-by-the-presence-of-required
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does direct pushes to main are blocked by the presence of required_pull_request_reviews, not by its review count — dropping count to 0 or DELETING the sub-resource doesn't free up direct push?

## Answer

tried to admin-push a release commit directly to main with `gh api -X PATCH ... -F required_approving_review_count=0` first, then `gh api -X DELETE repos/.../branches/main/protection/required_pull_request_reviews`. Both were accepted by the API, and both still produced ``` GH006: Protected branch update failed for refs/heads/main. - Changes must be made through a pull request. - Required status check "Analyze (python)" is expected. ``` on push. The "must go through PR" rule appears to be a derived property of having ANY combination of `required_linear_history: true`, `required_status_checks`, or `enforce_admins: true` — not of `required_pull_request_reviews` alone.

```
gh api -X PATCH ... -F required_approving_review_count=0
```

## Related Topics
- **Error**: Detailed error: Direct pushes to main are blocked by the
  presence of `required_pull_request_reviews`, not
  by its review count — dropping count to 0 or
  DELETING the sub-resource doesn't free up direct
  push
