---
type: troubleshooting
name: ci-tests-timeout
tags: [ci, testing, windows]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: CI tests timing out

## Symptom

GitHub Actions test matrix fails with timeout on one or more platforms.

## Diagnosis

1. Check which platform timed out (Windows is ~3x slower)
2. Look at `timeout-minutes` in the workflow YAML
3. Check if new tests were added that significantly increase runtime

## Fix

Increase `timeout-minutes` in the workflow YAML. Windows needs ~45-60 min for the full suite. Update `test_timeout_values_are_reasonable` test if the upper bound changed.

## Prevention

Set Windows timeout to 60 min. Run targeted coverage (`pytest tests/unit/module/`) during development.

## Related Topics

_No related topics yet._
