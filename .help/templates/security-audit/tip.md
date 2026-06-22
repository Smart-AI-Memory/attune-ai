---
type: tip
name: security-audit-tip
feature: security-audit
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Tip: Run the security audit before you ship, not after

Run `attune workflow run security-audit --path "src/"` as a pre-release gate, not a one-off check.

**Why:** `SecurityAuditWorkflow` coordinates four subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — in parallel. Catching a hardcoded secret or an unvalidated file path costs seconds at audit time and hours in an incident.

**How:** The workflow's `execute()` method returns findings grouped by severity (CRITICAL, HIGH, MEDIUM, LOW) with file paths, line numbers, and prioritized remediation steps. Treat any CRITICAL finding as a release blocker.

**Tradeoff:** A full multi-pass audit takes roughly five minutes. If you run it only on changed paths rather than the whole codebase, you may miss vulnerabilities introduced by transitive effects — a utility function used in a new, riskier context, for example.

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
