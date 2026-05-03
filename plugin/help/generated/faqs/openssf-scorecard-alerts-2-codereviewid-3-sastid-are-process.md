---
name: openssf-scorecard-alerts-2-codereviewid-3-sastid-are-process
source: .claude/CLAUDE.md
summary: This template explains that OpenSSF Scorecard alerts for Code Review and
  SAST measure process compliance rather than specific code bugs, and that improving
  these scores requires configuring branch protection rules to enforce mandatory code
  reviews and static analysis on all pull requests, after which scores will improve
  automatically over time.
type: faq
---

# FAQ: What should I know about OpenSSF Scorecard alerts for Code Review and SAST (process metrics, not code bugs)?

## Answer

OpenSSF Scorecard alerts for **Code Review** and **SAST** are process metrics — they measure the ratio of approved and analyzed changesets over time. Because they reflect historical patterns across many pull requests, no single PR can resolve them. Scores improve incrementally as future PRs flow through the required review and SAST gates.

**How to fix:**

Setting up the gates is the fix — the scores follow automatically as compliant PRs accumulate:

- **Code Review:** Configure branch protection rules to require a minimum number of approved reviews before merging.
- **SAST:** Add a required CodeQL (or equivalent) check to your branch protection rules so every PR is analyzed before it can be merged.

Once these gates are in place, scores will improve over time without any further manual intervention.

## Related Topics

- OpenSSF Scorecard — [Code Review check documentation](https://github.com/ossf/scorecard/blob/main/docs/checks.md#code-review)
- OpenSSF Scorecard — [SAST check documentation](https://github.com/ossf/scorecard/blob/main/docs/checks.md#sast)
- Configuring branch protection rules in GitHub
- Setting up CodeQL analysis with GitHub Actions
