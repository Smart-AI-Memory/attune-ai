---
type: troubleshooting
name: security-audit-troubleshooting
feature: security-audit
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Troubleshoot security audit

The `security-audit` feature scans your codebase for vulnerabilities including `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks. Use this page when `attune workflow run security-audit` produces an error, returns unexpected results, or behaves differently than described in the quickstart.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `SecurityViolation` raised unexpectedly | Confirm the path argument points to a readable directory; check `_validate_file_path` for path constraints |
| Audit completes but reports no findings | Verify `--path` resolves to the directory you intend — a typo silently scans an empty tree |
| `detect_secrets` returns false negatives | Confirm `SecretsDetector` is initialized; check whether the `SecretType` patterns cover your secret format |
| PII scrubbing strips data you need | Review `PIIPattern` configuration — an overly broad pattern can match legitimate content |
| `SecurityAuditWorkflow.execute()` hangs | One of the four subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) may be blocked waiting for the LLM; check network connectivity and API key validity |
| Output missing CRITICAL/HIGH severity section | The orchestrator prompt requires findings grouped by severity — if the LLM response is truncated, the synthesis step may silently drop sections |
| Intermittent `AuditLogger` failures | Check for file-locking conflicts if multiple processes write audit events concurrently |

## Diagnose the problem

Work through these checks in order — each step is cheaper than the next.

### 1. Reproduce with a minimal path

Run the audit against a single small file before pointing it at a full directory:

```bash
attune workflow run security-audit --path "src/your_module.py"
```

If that succeeds, the issue is scope-related (large directory, binary files, or symlinks). Narrow or widen from there.

### 2. Confirm the workflow reaches all four subagents

`SecurityAuditWorkflow` coordinates four subagents: `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner`. If the final report is missing an entire category (for example, no secret findings at all), one subagent may have failed silently. Re-run and check whether the Summary section mentions all four domains.

### 3. Check metrics and alert history

If you have alerts configured, verify current telemetry values before assuming a code defect:

```bash
attune alerts metrics
attune alerts history --limit 20
```

A spike in error rate or latency visible in `metrics` output often explains why a workflow behaves unexpectedly.

### 4. Verify secret detection directly

Call `detect_secrets` in isolation to confirm whether the detection layer itself is at fault:

```python
from security import detect_secrets

findings = detect_secrets("path/to/file.py")
print(findings)
```

If this returns results when the full workflow does not, the issue is in the `SecurityAuditWorkflow` orchestration layer, not in `SecretsDetector`.

### 5. Inspect `AuditLogger` output

`AuditLogger` records `AuditEvent` entries as the workflow runs. If the workflow exits without error but results look wrong, review the audit log for events that completed versus those that did not. A missing `AuditEvent` for a subagent indicates it was never invoked.

### 6. Run the related tests

```bash
pytest -k "security_audit" -v
```

A failing test that exercises your path confirms the bug is reproducible and gives you a fixture to work against.

## Common fixes

**Wrong or unreadable path**
`_validate_file_path` raises if the path is outside the allowed scope. Make sure the path you pass to `--path` exists and is readable by the process running attune:

```bash
ls -la src/          # confirm the directory exists and is accessible
attune workflow run security-audit --path "src/"
```

**Subagent blocked on LLM call**
If `SecurityAuditWorkflow.execute()` hangs, the most likely cause is a missing or expired API key. Confirm your environment variable is set and valid, then re-run. You do not need to change any workflow code.

**`detect_secrets` misses a secret type**
`SecretsDetector` matches against `SecretType` patterns. If a secret format in your codebase is not covered, you need to extend the pattern set — this requires a change outside the workflow itself, in the `security` module configuration.

**PII scrubbing removes too much**
`PIIScrubber` applies `PIIPattern` rules broadly. If legitimate content is being stripped, review the active patterns. Narrowing a `PIIPattern` regex is a change to the `security` module, not to `SecurityAuditWorkflow`.

**Report sections missing after a large scan**
The orchestrator synthesizes findings from all four subagents into a single report with Summary, Security, and Suggestions sections. If the LLM response is truncated due to token limits, later sections are dropped first. Reduce the scan scope with a more specific `--path` argument:

```bash
attune workflow run security-audit --path "src/api/"   # scope to one package
```

**Stale alert configuration**
If `attune alerts watch` is triggering unexpectedly during a security audit run, check whether an alert threshold is set too low for the metrics generated by a deep scan:

```bash
attune alerts list
attune alerts disable <alert_id>   # temporarily disable while investigating
```

## Source files

- `src/attune/workflows/security_audit.py` — `SecurityAuditWorkflow` and subagent orchestration
- `src/attune/security/` — `AuditLogger`, `AuditEvent`, `SecretsDetector`, `PIIScrubber`, `SecurityViolation`, `Severity`
- `src/attune/monitoring/` — `AlertEngine`, `AlertConfig`, `AlertEvent`, telemetry collection

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 60 (code fence) | error | `from security import …` — module not importable |
