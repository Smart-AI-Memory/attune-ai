---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: comparison
---

# Multi-pass code review across security, quality, and test gaps

## Comparison

Deep-review and **security-audit** are both SDK-native review
workflows reached with `attune workflow run <name>`, both
predictive (LLM judgment), but they trade breadth against depth.

| | `deep-review` | `security-audit` |
|---|---|---|
| **Scope** | Three domains in one pass: security, quality, test gaps | Security only |
| **Subagents** | Three: security / quality / test-gap reviewers | Four: vuln-scanner, secret-detector, auth-reviewer, remediation-planner |
| **Narrowing** | `focus` selects a subset of passes | Always the full security sweep |
| **Turn budget** | 15 / 30 / 50 (quick / standard / deep) | 10 / 20 / 40 |
| **Report sections** | Summary / Security / Quality / Test Gaps / Suggestions | Summary / Security / Suggestions |
| **Slug** | `attune workflow run deep-review` | `attune workflow run security-audit` |

Reach for **deep-review** when you want one consolidated
pre-merge read across correctness, maintainability, and test
coverage; reach for **security-audit** when the concern is
specifically the vulnerability surface and you want the deeper,
four-subagent security treatment. Run deep-review with
`focus=["security"]` for a quick security-only pass, or
security-audit for the thorough one.
