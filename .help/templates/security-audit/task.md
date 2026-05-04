---
type: task
feature: security-audit
depth: task
generated_at: 2026-05-04T02:23:32.648645+00:00
source_hash: e5fdcf8a70287f5c6e2e0987e337f663cf89f93c523e4652f0c8a45e6709471e
status: generated
---

# Work with security audit

Use security audit when you need to scan code for vulnerabilities like eval/exec usage, path traversal, hardcoded secrets, or injection risks before releasing a version or reviewing pull requests.

## Prerequisites

- Access to the project source code
- Familiarity with the `src/attune/workflows/security_audit.py` workflow file

## Configure the audit workflow

1. **Open the security audit workflow file.**
   Navigate to `src/attune/workflows/security_audit.py` where the `SecurityAuditWorkflow` class manages the four-subagent orchestration.

2. **Review the current subagent configuration.**
   The workflow coordinates four specialized subagents defined in `_SUBAGENT_NAMES`: vuln-scanner, secret-detector, auth-reviewer, and remediation-planner.

3. **Modify audit parameters if needed.**
   Update the `_TASK_PROMPT_TEMPLATE` to adjust what the subagents focus on, or change the `_SYSTEM_PROMPT` to alter how findings are synthesized.

## Set up monitoring alerts

1. **Initialize the alert engine.**
   Run `attune alerts init` to create alert rules for security violations or use the programmatic `AlertEngine` class.

2. **Configure metric thresholds.**
   Set up alerts for security-related metrics using `add_alert()` with appropriate `AlertMetric` values and severity levels.

3. **Test alert delivery.**
   Verify notifications work by running `attune alerts watch --once` to trigger a single check cycle.

## Run the security audit

1. **Execute the workflow.**
   Use `SecurityAuditWorkflow().execute(path="src/")` programmatically or trigger through the CLI interface.

2. **Review the structured output.**
   The workflow returns findings organized by severity (CRITICAL, HIGH, MEDIUM, LOW) with file paths and line numbers.

3. **Verify results include all vulnerability types.**
   Confirm the output covers code injection, path traversal, hardcoded secrets, SQL/command injection, SSRF, and weak cryptography as defined in the audit scope.

## Test your changes

Run `pytest -k "security"` to validate your modifications don't break existing security detection patterns.

You know the task worked when the audit produces a structured report with a security score (0-100), severity-grouped findings, and actionable remediation steps with effort estimates.

## Key files

- `src/attune/workflows/security_audit.py` — Main workflow orchestrator
- `src/attune/security/**` — Security detection modules
- `src/attune/monitoring/**` — Alert engine and telemetry systems
