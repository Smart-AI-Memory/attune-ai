---
type: error
name: enforce-admins-false-defeats-code-review-scorecard-check
confidence: Verified
tags: [ci]
source: .claude/CLAUDE.md
---

# Error: `enforce_admins: false` defeats Code-Review Scorecard check

## Signature

`enforce_admins: false` defeats Code-Review Scorecard check

## Root Cause

Even with `required_approving_review_count: 1`, admins bypass reviews when `enforce_admins` is off. Scorecard sees 0/25 approved changesets. For solo devs: enable `enforce_admins` and add an auto-approve workflow triggered by CI success.

## Resolution

1. Even with `required_approving_review_count: 1`, admins bypass reviews when `enforce_admins` is off

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
