---
type: warning
feature: security-audit
depth: warning
generated_at: 2026-04-19T18:43:51.854380+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security Audit cautions

## What to watch for

The security audit feature scans for vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks. While powerful, it has specific behaviors that can lead to unexpected results if you're not careful.

## Risk areas

**Alert configuration persistence issues**
The `AlertEngine` stores alert configurations in SQLite at `.attune/alerts.db`. If you modify alerts programmatically while the CLI watch process is running, your changes may be overwritten or lost due to concurrent database access.

**Path validation bypasses in large codebases**
When scanning directories with thousands of files, the path validation utilities may skip files that exceed internal limits or contain unusual Unicode characters. This can create blind spots where vulnerabilities go undetected.

**Telemetry backend failures masking audit problems**
The `MultiBackend` telemetry system continues operating even when individual backends fail. If the security audit relies on telemetry data that isn't being recorded due to backend failures, you may see incomplete or misleading results.

**Secret detection false negatives with encoded content**
The `SecretsDetector` checks for plaintext patterns but may miss Base64-encoded API keys, hex-encoded tokens, or secrets split across multiple lines. This is particularly risky in configuration files and test fixtures.

**Subagent coordination race conditions**
The `SecurityAuditWorkflow` runs four specialized subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) concurrently. If one subagent fails or times out, the final report may appear complete while missing an entire category of findings.

## How to avoid problems

1. **Verify alert persistence before production.** Test alert modifications by running `attune alerts list` before and after changes to confirm they persist correctly. Stop any running watch processes first.

2. **Check backend status regularly.** Use `get_failed_backends()` to identify telemetry failures that could affect audit accuracy. Reset failures with `reset_failures()` after addressing the underlying issues.

3. **Validate scan completeness.** For critical audits, cross-reference the file count in results with your expected scope. Run targeted scans on suspicious files that may have been skipped.

4. **Test secret detection with realistic samples.** Include encoded, obfuscated, and multi-line secrets in your test cases to verify detection coverage matches your threat model.

5. **Monitor subagent execution.** Check the workflow logs for subagent timeouts or failures. Re-run failed audits with smaller scope to isolate problematic files or directories.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
