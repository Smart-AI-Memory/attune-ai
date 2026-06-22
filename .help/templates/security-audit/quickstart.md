---
type: quickstart
name: security-audit-quickstart
feature: security-audit
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Quickstart: Run a security audit

Scan your codebase for vulnerabilities — eval/exec usage, path traversal, hardcoded secrets, and injection risks — using four specialized subagents coordinated by `SecurityAuditWorkflow`.

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

result = SecurityAuditWorkflow().execute(path="src/")
print(result)
```

**Result:** A unified report with three sections — **Summary** (security score 0–100 and executive summary), **Security** (findings grouped by severity: CRITICAL, HIGH, MEDIUM, LOW), and **Suggestions** (prioritized remediation steps with estimated effort).

## Steps

### 1. Install and verify the package

Confirm the `security` module is available:

```python
from attune.security import detect_secrets, SecretsDetector, AuditLogger
```

If this import fails, check that the package is installed in your current environment.

### 2. Run the audit

Pass the path you want to scan to `SecurityAuditWorkflow.execute()`:

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

workflow = SecurityAuditWorkflow()
result = workflow.execute(path="src/")
print(result)
```

The workflow coordinates four subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — and synthesizes their output into a single report.

### 3. Review findings by severity

The **Security** section of the report lists findings under `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW` headings, each with file paths and line numbers where available. Address `CRITICAL` and `HIGH` findings first.

### 4. Apply remediation steps

The **Suggestions** section lists actionable fixes ordered by priority, with an estimated effort for each. Work through them top to bottom.

**Next:** After resolving critical issues, run `attune workflow run test-gen` to generate tests for the affected code paths.
