---
type: error
name: openssf-scorecard-alerts-2-codereviewid-3-sastid-are-process
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: OpenSSF Scorecard alerts (#2 CodeReviewID, #3 SASTID) are
  process metrics, not code bugs

## Signature

OpenSSF Scorecard alerts (#2 CodeReviewID, #3 SASTID) are
  process metrics, not code bugs

## Root Cause

They measure the ratio of approved/analyzed changesets over time. No single PR can fix them — they improve incrementally as future PRs flow through review and SAST gates. Setting up the gates (required reviews, required CodeQL checks) is the fix; the score follows.

## Resolution

1. Setting up the gates (required reviews, required CodeQL checks) is the fix; the score follows

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
