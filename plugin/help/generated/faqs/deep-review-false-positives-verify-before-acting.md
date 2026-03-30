---
type: faq
name: deep-review-false-positives-verify-before-acting
tags: [testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Deep review false positives — verify before acting?

## Answer

The quality pass reported `summary_index.py` at 0% coverage and `test_runner_helpers.py` missing docstrings. Both were wrong — `summary_index.py` had 25 tests in `tests/memory/`, and all helpers had docstrings.


**Fix:**

- Always re-verify agent findings against the actual codebase before planning fixes

```
summary_index.py
```

## Related Topics
- **Error**: Detailed error: Deep review false positives — verify before acting
