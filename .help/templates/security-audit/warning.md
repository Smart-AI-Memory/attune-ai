---
type: warning
name: security-audit-warning
feature: security-audit
depth: warning
generated_at: 2026-05-16T06:19:45.808049+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645761ffa7e81668
status: generated
---

# Security Audit cautions

## What to watch for

The security audit scans for eval/exec usage, path traversal, hardcoded secrets, and injection risks. The risks below apply to how the audit itself is configured and run — not just to the code it scans.

## Risk areas

**Hardcoded secrets committed before a scan runs**
The `secret-detector` subagent finds secrets already in source control, but it cannot prevent a secret from being committed in the same change that introduces the audit. Run `attune workflow run security-audit --path "src/"` as a CI gate on every pull request, not just before releases, so secrets are caught before they merge.

**Alert thresholds that never fire**
`AlertEngine.add_alert()` accepts a `threshold: float` with no validation against the actual range of the target `AlertMetric`. A threshold set too high will silently pass every `check_and_trigger()` call without raising an `AlertEvent`. After creating an alert, call `get_metrics()` to confirm the current metric value is in a range where your threshold is reachable.

**Alert cooldown masking repeated violations**
`AlertConfig.cooldown_seconds` defaults to `3600`. If a metric breaches its threshold repeatedly within that window, only the first `AlertEvent` is recorded. In high-frequency scanning environments, set a shorter cooldown or call `get_alert_history()` to confirm whether suppressed events exist before concluding a metric is healthy.

**Disabled alerts that look active**
`AlertConfig.enabled` defaults to `True`, but `disable_alert()` persists the change to SQLite. If you disable an alert for debugging and forget to re-enable it, `list_alerts()` will still show the alert — it just won't fire. Check the `enabled` field in the output of `list_cmd()` before assuming coverage is complete.

**`MultiBackend` silently dropping telemetry**
`MultiBackend.log_call()` continues if one backend fails, logging the failure internally rather than raising an exception. Call `get_failed_backends()` periodically — or after any infrastructure change — to confirm no backend has entered a failed state and is silently discarding records that `AlertEngine` depends on.

**Private subagent names and prompt templates**
`_SUBAGENT_NAMES` and `_TASK_PROMPT_TEMPLATE` are underscore-prefixed module constants. They are not part of the public API and can change between releases. If you build tooling that parses audit output based on subagent names (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) or on the report's section structure, that tooling may break without a deprecation notice.

## How to avoid problems

1. **Verify alert reachability after setup.** After calling `add_alert()`, run `get_metrics()` and confirm the current metric value would cross your threshold under realistic conditions. An unreachable threshold is indistinguishable from no alert at all.

2. **Check backend health before relying on alert history.** Call `get_failed_backends()` on `MultiBackend` before treating `get_alert_history()` results as authoritative. Missing telemetry records mean `check_and_trigger()` evaluates incomplete data.

3. **Use the workflow output, not internal constants.** Consume audit results through `SecurityAuditWorkflow.execute()` and parse the structured markdown sections (`## Summary`, `## Security`, `## Suggestions`) rather than keying on subagent names or prompt structure that may change.

4. **Re-enable alerts explicitly after maintenance.** After any debugging session where you called `disable_alert()`, call `enable_alert()` and confirm with `list_cmd()` that the `enabled` field is `True`.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
