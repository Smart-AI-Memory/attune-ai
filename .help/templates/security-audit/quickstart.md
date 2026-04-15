---
type: quickstart
feature: security-audit
depth: quickstart
generated_at: 2026-04-14T14:39:44.252211+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Quickstart: security audit

Run a security audit on your codebase to detect vulnerabilities, hardcoded secrets, and authentication issues.

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

audit = SecurityAuditWorkflow()
result = audit.execute(path="./your-project")
print(result.content)
```

## Run your first security audit

1. **Create the workflow instance** and point it at your codebase:

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

audit = SecurityAuditWorkflow()
result = audit.execute(path="./src")
```

2. **Review the audit report** which includes a security score and organized findings:

```
## Summary
Security Score: 78/100
The codebase shows good security practices with minor vulnerabilities requiring attention.

## Security
### HIGH
- Hardcoded API key detected in config/settings.py:15
- SQL injection risk in user_queries.py:42

### MEDIUM
- Missing input validation in auth/login.py:28

## Suggestions
1. Move API keys to environment variables (HIGH priority, 15min effort)
2. Implement parameterized queries (HIGH priority, 30min effort)
```

3. **Set up monitoring alerts** to catch security issues automatically:

```python
from attune.monitoring.alerts import get_alert_engine

engine = get_alert_engine()
engine.add_alert(
    alert_id="security_threshold",
    name="Security Score Alert",
    metric="security_score",
    threshold=70.0,
    channel="webhook",
    webhook_url="https://your-webhook.com/alerts"
)
```

## Expected output

The security audit produces a structured markdown report with:
- Overall security score (0-100)
- Findings organized by severity (CRITICAL, HIGH, MEDIUM, LOW)
- Actionable remediation steps with effort estimates
- File paths and line numbers for each issue

## Next

Run `attune alerts watch` to monitor your telemetry and receive notifications when security scores drop below your threshold.
