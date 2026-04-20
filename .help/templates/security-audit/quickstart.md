---
type: quickstart
feature: security-audit
depth: quickstart
generated_at: 2026-04-19T18:44:41.999441+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Quickstart: Security audit

Run a comprehensive security scan using four specialized subagents: vulnerability scanner, secret detector, authentication reviewer, and remediation planner.

```python
from attune.workflows import SecurityAuditWorkflow

workflow = SecurityAuditWorkflow()
result = workflow.execute(path="src/")
print(result.content)
```

**Result:** Structured security report with severity-grouped findings, overall security score (0-100), and prioritized remediation steps.

## Steps

1. **Create the workflow instance** with default settings
2. **Execute the audit** on your target directory
3. **Review the findings** organized by CRITICAL, HIGH, MEDIUM, LOW severity

## Expected output

```
## Summary
Security score: 85/100
The codebase shows good security practices with minor improvements needed.

## Security
### CRITICAL
- None found

### HIGH
- Hardcoded API key detected in config/settings.py:23
...
```

**Next:** Address critical and high-severity issues, then run `attune workflow run test-gen`.
