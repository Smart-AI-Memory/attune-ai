---
type: task
feature: security-audit
depth: task
generated_at: 2026-04-19T18:42:58.129712+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Work with security audit

Use security audit when you need to scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, injection risks.

## Prerequisites

- Access to the project source code
- Familiarity with the `SecurityAuditWorkflow` class and its four specialized subagents

## Examine the workflow structure

1. Open `src/attune/workflows/security_audit.py` to review the `SecurityAuditWorkflow` class.

2. Check the `_SUBAGENT_NAMES` constant to see the four specialized subagents:
   - vuln-scanner
   - secret-detector
   - auth-reviewer
   - remediation-planner

3. Review the `execute()` method to see how subagents coordinate to produce the unified security report.

## Modify workflow behavior

1. **Update subagent coordination**: Edit the `execute()` method in `SecurityAuditWorkflow` to change how the four subagents work together.

2. **Adjust the system prompt**: Modify `_SYSTEM_PROMPT` to change the workflow's overall orchestration behavior.

3. **Customize task prompts**: Update `_TASK_PROMPT_TEMPLATE` to change what each subagent focuses on during audits.

## Configure monitoring and alerts

1. **Set up telemetry monitoring**: Use the `AlertEngine` class to monitor security audit metrics and trigger alerts.

2. **Add alert configurations**: Call `AlertEngine.add_alert()` to create alerts for security thresholds like critical vulnerability counts.

3. **Configure notification channels**: Set up webhook URLs or email addresses in `AlertConfig` for alert delivery.

## Test your changes

Run targeted tests to verify your modifications work correctly:

```bash
pytest -k "security-audit"
```

This catches regressions in the security audit workflow before they affect other developers.

## Key files

- `src/attune/workflows/security_audit.py` — Main workflow orchestrator
- `src/attune/security/` — Security detection modules
- `src/attune/monitoring/alerts_cli.py` — Alert management commands
- `src/attune/telemetry/` — Telemetry backend for monitoring

## Verify success

You know your changes work when:
- The security audit produces structured findings grouped by severity
- Any new alerts trigger correctly when thresholds are exceeded
- The workflow coordinates all four subagents without errors
- Test suite passes with no regressions
