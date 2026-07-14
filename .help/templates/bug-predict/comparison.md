---
type: comparison
name: bug-predict-comparison
feature: bug-predict
depth: comparison
generated_at: 2026-07-14T22:05:25.786099+00:00
source_hash: 6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208
status: generated
---

# Predict likely bug hotspots with three Agent SDK subagents

## Comparison

Bug-predict and **security-audit** both scan the same codebase
through Agent SDK subagents and are both reached with
`attune workflow run <name>`, but they answer different
questions.

| | `bug-predict` | `security-audit` |
|---|---|---|
| **Question answered** | "Where are bugs most likely to be?" | "Where are the security vulnerabilities?" |
| **Focus** | Correctness-risk hotspots: null refs, type mismatches, race conditions, broad excepts, resource leaks, off-by-one | Security issues: `eval`/`exec`, path traversal, injection, hardcoded secrets |
| **Output** | Overall risk score + bugs by severity + prevention advice | Vulnerability findings by severity |
| **Slug** | `attune workflow run bug-predict` | `attune workflow run security-audit` |
| **Nature** | Predictive (LLM judgment), not a deterministic linter | Predictive (LLM judgment), not a deterministic linter |

Reach for **bug-predict** when you want a broad correctness-risk
triage of a module; reach for **security-audit** when the concern
is specifically a vulnerability surface. They overlap on
`eval`/`exec` (both flag it) and complement each other on a
pre-release sweep.
