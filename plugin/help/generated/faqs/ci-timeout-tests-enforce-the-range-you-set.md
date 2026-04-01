---
type: faq
name: ci-timeout-tests-enforce-the-range-you-set
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: Why does CI timeout tests enforce the range you set?

## Answer

The test `test_timeout_values_are_reasonable` in `tests/unit/ci/` asserts that all workflow job timeouts fall within an allowed range. When bumping `timeout-minutes` in a workflow YAML, also update the test's upper bound or it fails on every platform.

```
test_timeout_values_are_reasonable
```

## Related Topics
- **Error**: Detailed error: CI timeout tests enforce the range you set
