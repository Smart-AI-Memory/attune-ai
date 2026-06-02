---
type: tip
name: security-audit-tip
feature: security-audit
depth: tip
generated_at: 2026-06-02T10:56:02.709415+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Tip: Run the security audit before you ship, not after

Run `attune workflow run security-audit --path "src/"` as a pre-release gate, not a one-off check.

**Why:** `SecurityAuditWorkflow` coordinates four subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — in parallel. Catching a hardcoded secret or an unvalidated file path costs seconds at audit time and hours in an incident.

**How:** The workflow's `execute()` method returns findings grouped by severity (CRITICAL, HIGH, MEDIUM, LOW) with file paths, line numbers, and prioritized remediation steps. Treat any CRITICAL finding as a release blocker.

**Tradeoff:** A full multi-pass audit takes roughly five minutes. If you run it only on changed paths rather than the whole codebase, you may miss vulnerabilities introduced by transitive effects — a utility function used in a new, riskier context, for example.

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
