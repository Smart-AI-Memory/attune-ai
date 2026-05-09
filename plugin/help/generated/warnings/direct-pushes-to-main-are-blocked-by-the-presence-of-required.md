---
type: warning
name: direct-pushes-to-main-are-blocked-by-the-presence-of-required
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: Direct pushes to main are blocked by the
  presence of `required_pull_request_reviews`, not
  by its review count — dropping count to 0 or
  DELETING the sub-resource doesn't free up direct
  push

## Condition

tried to admin-push a release commit directly to main with `gh api -X PATCH ... -F required_approving_review_count=0` first, then `gh api -X DELETE repos/.../branches/main/protection/required_pull_request_reviews`

## Risk

Both were accepted by the API, and both still produced ``` GH006: Protected branch update failed for refs/heads/main. - Changes must be made through a pull request. - Required status check "Analyze (python)" is expected. ``` on push. The "must go through PR" rule appears to be a derived property of having ANY combination of `required_linear_history: true`, `required_status_checks`, or `enforce_admins: true` — not of `required_pull_request_reviews` alone

## Mitigation

1. tried to admin-push a release commit directly to main with `gh api -X PATCH ... -F required_approving_review_count=0` first, then `gh api -X DELETE repos/.../branches/main/protection/required_pull_request_reviews`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Direct pushes to main are blocked by the
  presence of `required_pull_request_reviews`, not
  by its review count — dropping count to 0 or
  DELETING the sub-resource doesn't free up direct
  push
