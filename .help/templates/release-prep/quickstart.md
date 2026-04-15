---
type: quickstart
feature: release-prep
depth: quickstart
generated_at: 2026-04-14T14:51:12.292401+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Quickstart: release prep

Run a comprehensive release readiness assessment on your codebase:

```python
from attune.agents.release import ReleasePrepTeam

team = ReleasePrepTeam()
report = team.assess_readiness()
print(report.format_console_output())
```

## Run the assessment

1. **Create a release preparation team** with default quality gates:
   ```python
   from attune.agents.release import ReleasePrepTeam

   team = ReleasePrepTeam()
   ```

2. **Assess your codebase** in the current directory:
   ```python
   report = team.assess_readiness()
   ```

3. **View the results** to see if your code is release-ready:
   ```python
   print(f"Release approved: {report.approved}")
   print(report.format_console_output())
   ```

## Expected output

The assessment produces a structured report showing:

```
Release Readiness Report
========================
Status: APPROVED ✓
Confidence: HIGH

Quality Gates:
✓ Test Coverage: 85.2% (threshold: 80%)
✓ Documentation: 92% coverage
✗ Security: 2 vulnerabilities found
✓ Code Quality: No critical issues

Blockers: 0 | Warnings: 1
Total Cost: $0.45 | Duration: 12.3s
```

If `report.approved` is `False`, check `report.blockers` for issues that must be resolved before release.

## Next steps

Customize quality gate thresholds by passing a `quality_gates` dictionary to `ReleasePrepTeam()` to match your project's requirements.
