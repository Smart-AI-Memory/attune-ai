---
type: task
name: security-audit-task
feature: security-audit
depth: task
generated_at: 2026-05-16T06:19:45.792876+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Run a security audit

Use `attune workflow run security-audit` when you want to scan a codebase for vulnerabilities — eval/exec usage, path traversal, hardcoded secrets, and injection risks — and receive a severity-grouped report with actionable remediation steps.

## Prerequisites

- Access to the project source code you want to scan
- The `attune` CLI installed and accessible on your `PATH`

## Run the audit

1. **Choose the path to scan.**
   Identify the directory or file you want to audit. For most projects, `src/` is a good starting point.

2. **Run the workflow.**

   ```
   attune workflow run security-audit --path "src/"
   ```

   The workflow coordinates four specialized subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — and then synthesizes their output into a single report.

3. **Review the report.**
   The output is organized into three sections:

   - **Summary** — an overall security score (0–100) and a short executive summary of the security posture.
   - **Security** — consolidated findings ordered by severity: CRITICAL, HIGH, MEDIUM, and LOW. Each finding includes a file path and line number where available.
   - **Suggestions** — prioritized remediation steps with an estimated effort for each fix.

4. **Address critical findings first.**
   Work through findings in severity order. After applying fixes, re-run the audit against the same path to confirm the issues no longer appear in the report.

5. **Verify success.**
   The audit has completed successfully when the report renders all three sections and no CRITICAL findings remain for the code you changed. Run `attune workflow run test-gen` next to generate tests that cover the corrected code paths.

## Key files

- `src/attune/workflows/security_audit.py` — `SecurityAuditWorkflow` class and subagent orchestration
- `src/attune/security/` — secret detection, PII scrubbing, and audit logging utilities
- `src/attune/monitoring/` — alert engine and CLI commands for threshold-based monitoring

## Extend or customize the audit

To change how the audit behaves, locate the function that owns the specific responsibility you need to modify:

| Function | File | Responsibility |
|---|---|---|
| `SecurityAuditWorkflow.execute()` | `src/attune/workflows/security_audit.py` | Orchestrates the four subagents and produces the final report |
| `watch()` | `src/attune/monitoring/alerts_cli.py` | Monitors telemetry continuously and triggers alerts when thresholds are exceeded |
| `init()` | `src/attune/monitoring/alerts_cli.py` | Configures a new alert interactively or from CLI flags |
| `history()` | `src/attune/monitoring/alerts_cli.py` | Retrieves past alert trigger events |
| `enable()` / `disable()` | `src/attune/monitoring/alerts_cli.py` | Toggles an alert on or off by ID |

After editing, run `pytest -k "security-audit"` to catch regressions before sharing your changes.
