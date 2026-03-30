---
type: faq
name: openssf-scorecard-alerts-2-codereviewid-3-sastid-are-process
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: OpenSSF Scorecard alerts (#2 CodeReviewID, #3 SASTID) are
  process metrics, not code bugs?

## Answer

They measure the ratio of approved/analyzed changesets over time. No single PR can fix them — they improve incrementally as future PRs flow through review and SAST gates.


**Fix:**

- Setting up the gates (required reviews, required CodeQL checks) is the fix; the score follows

## Related Topics
- **Error**: Detailed error: OpenSSF Scorecard alerts (#2 CodeReviewID, #3 SASTID) are
  process metrics, not code bugs
