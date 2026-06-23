---
type: comparison
name: security-audit-comparison
feature: security-audit
depth: comparison
generated_at: 2026-06-23T12:50:51.607005+00:00
source_hash: e6418a3912ca1198d747373f96c129051dd6130394ad9f787b25fd12acf68e4a
status: generated
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Comparison

Security-audit and **bug-predict** are sibling SDK-native
workflows — both scan the same codebase through Agent SDK
subagents, both reached with `attune workflow run <name>`, both
predictive (LLM judgment) — but they answer different questions.

| | `security-audit` | `bug-predict` |
|---|---|---|
| **Question answered** | "Where are the security vulnerabilities?" | "Where are bugs most likely to be?" |
| **Subagents** | Four: vuln-scanner, secret-detector, auth-reviewer, remediation-planner | Three: pattern-scanner, risk-correlator, prevention-advisor |
| **Focus** | Injection, secrets, auth/access control, path traversal | Correctness-risk hotspots: null refs, type mismatches, race conditions, resource leaks |
| **Severity scale** | CRITICAL / HIGH / MEDIUM / LOW | HIGH / MEDIUM / LOW |
| **Slug** | `attune workflow run security-audit` | `attune workflow run bug-predict` |

Reach for **security-audit** when the concern is a vulnerability
surface — secrets, injection, access control; reach for
**bug-predict** for a broad correctness-risk triage. They overlap
on `eval`/`exec` (both flag it) and pair well on a pre-release
sweep.
