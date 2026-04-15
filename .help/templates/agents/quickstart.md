---
type: quickstart
feature: agents
depth: quickstart
generated_at: 2026-04-14T15:09:54.476612+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Quickstart: agents

Run a release readiness assessment on your codebase using AI agents that check test coverage, documentation, and code quality.

```python
from attune.agents import ReleasePrepTeam

team = ReleasePrepTeam()
report = team.assess_readiness('.')
print(report.format_console_output())
```

## Check your codebase

1. **Run the assessment** on your current directory:
   ```python
   from attune.agents import ReleasePrepTeam

   team = ReleasePrepTeam()
   report = team.assess_readiness()
   ```

2. **Review the results**. The report shows pass/fail status for each quality gate:
   ```python
   print(f"Release approved: {report.approved}")
   print(f"Confidence: {report.confidence}")
   for gate in report.quality_gates:
       print(f"{gate.name}: {'PASS' if gate.passed else 'FAIL'}")
   ```

3. **Check the details** to see what needs fixing:
   ```python
   if report.blockers:
       print("Blockers:")
       for blocker in report.blockers:
           print(f"  - {blocker}")
   ```

Expected output shows quality gates like test coverage, documentation coverage, and code quality checks with pass/fail status and specific recommendations.

## Next:

Configure custom quality gate thresholds using the `quality_gates` parameter in `ReleasePrepTeam.__init__()` to match your project's standards.
