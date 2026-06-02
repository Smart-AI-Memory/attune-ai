---
type: task
name: security-audit-task
feature: security-audit
depth: task
generated_at: 2026-06-02T10:56:02.680360+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Run a security audit

Use `SecurityAuditWorkflow` when you want to scan a codebase for vulnerabilities — including `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks — and receive a severity-grouped report with actionable remediation steps.

## Prerequisites

- Access to the project source code you want to scan
- The `attune` package installed with the `workflows` and `security` modules available

## Run the audit

1. **Import and instantiate `SecurityAuditWorkflow`.**

   ```python
   from attune.workflows.security_audit import SecurityAuditWorkflow

   workflow = SecurityAuditWorkflow()
   ```

   Pass `system_prompt_suffix` if you want to append additional instructions to the orchestrator prompt:

   ```python
   workflow = SecurityAuditWorkflow(system_prompt_suffix="Focus on authentication code only.")
   ```

2. **Call `execute()` with the path to scan.**

   ```python
   result = workflow.execute(path="src/")
   ```

   The workflow coordinates four specialized subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — and synthesizes their output into a single report.

3. **Inspect the returned `WorkflowResult`.**

   The report contains three sections:

   - **Summary** — an overall security score (0–100) and a brief executive summary
   - **Security** — consolidated findings grouped by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
   - **Suggestions** — prioritized remediation steps with estimated effort per fix

4. **Run the audit from the CLI** (alternative to the Python API).

   ```
   attune workflow run security-audit --path "src/"
   ```

   The CLI produces the same severity-grouped findings with CWE identifiers.

## Verify success

The audit completed successfully when `WorkflowResult` contains all three report sections — **Summary**, **Security**, and **Suggestions** — and the **Summary** section includes a numeric security score. If findings exist, they appear under **Security** with at least one severity label (`CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`).

## Key files

- `src/attune/workflows/security_audit.py` — `SecurityAuditWorkflow` and its four subagent definitions
- `src/attune/security/` — `SecretsDetector`, `PIIScrubber`, `AuditLogger`, and related detection primitives
- `src/attune/monitoring/alerts_cli.py` — CLI commands (`watch`, `history`, `metrics`) for monitoring audit-related telemetry thresholds
