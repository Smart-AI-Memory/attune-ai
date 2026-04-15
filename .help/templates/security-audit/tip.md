---
type: tip
feature: security-audit
depth: tip
generated_at: 2026-04-14T14:39:56.808895+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Set up security alerts before running audits

Start your security workflow by configuring AlertEngine to monitor for suspicious patterns during code analysis. The alert system catches security violations in real-time while the SecurityAuditWorkflow runs its four specialized subagents.

```python
from attune.monitoring.alerts import AlertEngine, AlertMetric, AlertChannel

engine = AlertEngine()
engine.add_alert(
    alert_id="security_violations",
    name="Critical Security Issues",
    metric=AlertMetric.ERROR_RATE,
    threshold=0.1,  # 10% error rate
    channel=AlertChannel.WEBHOOK
)
```

Configure alerts for secret detection failures and path traversal attempts before you scan large codebases — catching issues early prevents having to re-audit after fixing monitoring gaps.

**Tags:** `security`, `audit`, `owasp`, `scanning`
