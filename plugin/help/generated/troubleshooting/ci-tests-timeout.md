---
name: ci-tests-timeout
source: CLAUDE.md Lessons Learned
summary: This template guides developers through identifying, diagnosing, and resolving
  CI test timeouts in GitHub Actions workflows, with particular attention to platform-specific
  performance differences and preventive strategies.
tags:
- ci
- testing
- windows
type: troubleshooting
---

# Troubleshooting: CI Tests Timing Out

## Symptom

One or more platforms fail in the GitHub Actions test matrix with a timeout error.

## Diagnosis

1. Identify which platform timed out — Windows runners are typically ~3× slower than Linux.
2. Review the `timeout-minutes` value in the workflow YAML.
3. Check whether recently added tests have significantly increased the total runtime.

## Fix

Increase `timeout-minutes` in the workflow YAML for the affected platform. The full test suite on Windows generally requires **45–60 minutes**. If you raise the upper bound, also update the `test_timeout_values_are_reasonable` test to reflect the new limit.

## Prevention

- Set the Windows job timeout to **60 minutes** as a baseline.
- During development, run targeted coverage instead of the full suite:
  ```
  pytest tests/unit/module/
  ```

## Related Topics

_No related topics yet._
