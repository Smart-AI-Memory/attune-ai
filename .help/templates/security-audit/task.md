---
type: task
feature: security-audit
depth: task
generated_at: 2026-04-14T14:37:58.750484+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Run a security audit

Run a security audit when you need to scan your codebase for vulnerabilities, secrets, authentication flaws, and security violations before deployment or code review.

## Prerequisites

- Python environment with Attune AI installed
- Access to the codebase you want to audit
- Write permissions for the `.attune` directory (for alert storage)

## Execute the security audit

1. **Initialize the security audit workflow**
   ```python
   from attune.workflows.security_audit import SecurityAuditWorkflow

   workflow = SecurityAuditWorkflow()
   ```

2. **Run the audit on your codebase**
   ```python
   result = workflow.execute(path="/path/to/your/code")
   ```

3. **Review the structured report**
   The workflow returns a `WorkflowResult` containing:
   - Overall security score (0-100)
   - Executive summary of security posture
   - Findings organized by severity (CRITICAL, HIGH, MEDIUM, LOW)
   - Actionable remediation steps with effort estimates

## Set up alert monitoring

1. **Initialize alert configuration**
   ```bash
   attune alerts init
   ```
   Follow the interactive prompts to configure metric thresholds, notification channels, and delivery settings.

2. **Create alerts programmatically**
   ```python
   from attune.monitoring.alerts import get_alert_engine, AlertMetric, AlertChannel, AlertSeverity

   engine = get_alert_engine()
   engine.add_alert(
       alert_id="security-violations",
       name="Security Violation Threshold",
       metric=AlertMetric.SECURITY_VIOLATIONS,
       threshold=5.0,
       channel=AlertChannel.EMAIL,
       email="security@yourcompany.com",
       severity=AlertSeverity.CRITICAL
   )
   ```

3. **Start monitoring**
   ```bash
   attune alerts watch --interval 300
   ```

## Verify audit completion

The security audit succeeds when:
- The `WorkflowResult` contains findings from all four subagents: vulnerability scanner, secret detector, authentication reviewer, and remediation planner
- Each finding includes file paths and line numbers where issues were detected
- The report shows an overall security score and prioritized remediation steps
- Alert monitoring (if configured) shows active alerts in `attune alerts list`
