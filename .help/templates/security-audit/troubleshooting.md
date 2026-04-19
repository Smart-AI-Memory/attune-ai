---
type: troubleshooting
feature: security-audit
depth: troubleshooting
generated_at: 2026-04-19T18:44:09.744562+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Troubleshoot security audit

## Before you start

The security audit feature scans your code for vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks. It uses four specialized subagents: vuln-scanner, secret-detector, auth-reviewer, and remediation-planner.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `SecurityAuditWorkflow.execute()` raises an exception | Python's traceback shows the exact file and line — start there |
| Audit completes but returns empty findings | Verify the scan path exists and contains readable files |
| Missing critical vulnerabilities in results | Check if the target files contain patterns the subagents recognize |
| Alert engine fails to trigger notifications | Confirm alert configuration with `attune alerts list` and verify webhook/email settings |
| Slow audit performance on large codebases | Monitor which subagent is bottlenecking — each focuses on different file types |

## Step-by-step diagnosis

1. **Test with a minimal scan target.**
   Create a simple test file with known security issues (like `eval(input())`) and scan just that file. If this fails, the problem is in the audit engine itself.

2. **Check the audit path and permissions.**
   Verify the target path exists and is readable:
   ```bash
   ls -la /path/to/scan
   stat /path/to/scan
   ```

3. **Run with debug logging.**
   Enable verbose output to see which subagent is failing:
   ```bash
   export ATTUNE_LOG_LEVEL=DEBUG
   attune workflow run security-audit --path "src/"
   ```

4. **Inspect subagent execution.**
   The audit uses four subagents. Check if specific ones are failing by examining the consolidated report structure — missing sections indicate subagent failures.

5. **Test alert configuration.**
   If alerts aren't working, verify your setup:
   ```bash
   attune alerts metrics
   attune alerts list
   ```

## Common fixes

- **Path not found errors:** Use absolute paths or verify your working directory. The audit expects valid filesystem paths, not patterns or globs.

- **Empty scan results:** Ensure you're scanning source code files (`.py`, `.js`, `.java`, etc.). The subagents skip binary files and some extensions by design.

- **Alert engine database issues:** Delete and reinitialize the alerts database:
  ```bash
  rm .attune/alerts.db
  attune alerts init
  ```

- **OTEL backend connection failures:** Check if your OpenTelemetry collector endpoint is reachable. Disable OTEL if not needed:
  ```python
  # In your workflow config, use only local backends
  backend = MultiBackend.from_config(storage_dir='.attune')
  ```

- **Webhook delivery failures:** Test your webhook URL manually before configuring alerts. The system validates webhook URLs but doesn't test connectivity.

- **Memory issues on large codebases:** Scan directories incrementally rather than the entire project at once. Each subagent processes files independently but all run concurrently.

## Source files

- `src/attune/workflows/security_audit.py` — Main SecurityAuditWorkflow class
- `src/attune/security/` — Security detection modules and utilities
- `src/attune/monitoring/` — Alert engine and telemetry systems

**Tags:** `security`, `audit`, `owasp`, `scanning`
